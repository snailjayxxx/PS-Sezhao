from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .project_store import normalized_file_path
from .roll_project_store import RollProjectStore, StoredRollProject


ARCHIVE_FORMAT = "ps-sezhao-roll-project"
ARCHIVE_SCHEMA_VERSION = 1
ARCHIVE_SUFFIX = ".psszproj"
MANIFEST_NAME = "manifest.json"
SOURCE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS project_source_identities (
    project_id TEXT NOT NULL,
    current_file_path TEXT NOT NULL,
    original_path TEXT NOT NULL DEFAULT '',
    original_name TEXT NOT NULL DEFAULT '',
    source_size INTEGER,
    source_mtime_ns INTEGER,
    source_sha256 TEXT NOT NULL DEFAULT '',
    archive_member TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(project_id, current_file_path),
    FOREIGN KEY(project_id) REFERENCES roll_projects(project_id) ON DELETE CASCADE
);
"""


@dataclass(frozen=True)
class SourceIdentity:
    current_file_path: str
    original_path: str
    original_name: str
    size: int | None
    mtime_ns: int | None
    sha256: str
    archive_member: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_file_path": self.current_file_path,
            "original_path": self.original_path,
            "original_name": self.original_name,
            "size": self.size,
            "mtime_ns": self.mtime_ns,
            "sha256": self.sha256,
            "archive_member": self.archive_member,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "SourceIdentity":
        payload = dict(value or {})
        return cls(
            current_file_path=str(payload.get("current_file_path") or ""),
            original_path=str(payload.get("original_path") or ""),
            original_name=str(payload.get("original_name") or ""),
            size=_optional_int(payload.get("size")),
            mtime_ns=_optional_int(payload.get("mtime_ns")),
            sha256=str(payload.get("sha256") or "").lower(),
            archive_member=str(payload.get("archive_member") or ""),
        )


@dataclass(frozen=True)
class ArchiveInspection:
    path: Path
    project_name: str
    item_count: int
    bundled_original_count: int
    missing_original_count: int
    schema_version: int

    @property
    def contains_originals(self) -> bool:
        return self.bundled_original_count > 0


@dataclass(frozen=True)
class ArchiveExportResult:
    path: Path
    item_count: int
    bundled_original_count: int
    missing_original_count: int
    sha256: str


@dataclass(frozen=True)
class ArchiveImportResult:
    project_id: str
    project_name: str
    item_count: int
    extracted_original_count: int
    missing_original_count: int


@dataclass(frozen=True)
class RelinkResult:
    project_id: str
    relinked_count: int
    unresolved_count: int
    ambiguous_count: int
    mappings: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ProjectIntegrityReport:
    project_id: str
    project_name: str
    total: int
    available: int
    missing_paths: tuple[str, ...]
    changed_paths: tuple[str, ...]
    hash_mismatches: tuple[str, ...]
    empty_frame_numbers: tuple[str, ...]
    duplicate_frame_numbers: tuple[str, ...]
    missing_output_preset: bool

    @property
    def ok(self) -> bool:
        return not (
            self.missing_paths
            or self.changed_paths
            or self.hash_mismatches
            or self.duplicate_frame_numbers
            or self.missing_output_preset
        )


def export_project_archive(
    store: RollProjectStore,
    project_id: str,
    destination: str | Path,
    *,
    include_originals: bool = False,
    calculate_hashes: bool = True,
) -> ArchiveExportResult:
    project = store.load_project(project_id)
    if project is None:
        raise KeyError(f"找不到胶卷项目：{project_id}")
    output_path = _archive_destination(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    identities = load_source_identities(store, project_id)
    preset = (
        store.load_output_preset(project.output_preset_id)
        if project.output_preset_id
        else None
    )
    current_position = None
    if project.current_file:
        current_key = normalized_file_path(project.current_file)
        for item in project.items:
            if normalized_file_path(item.file_path) == current_key:
                current_position = item.position
                break

    item_payloads: list[dict[str, Any]] = []
    missing = 0
    bundled = 0
    temporary = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            for item in project.items:
                source_path = Path(item.file_path)
                stored_identity = identities.get(normalized_file_path(source_path))
                identity = _identity_for_export(
                    source_path,
                    stored_identity,
                    calculate_hash=calculate_hashes,
                )
                member = ""
                if source_path.is_file() and include_originals:
                    member = _original_member(item.position, source_path.name)
                    archive.write(source_path, member, compress_type=zipfile.ZIP_STORED)
                    bundled += 1
                elif not source_path.is_file():
                    missing += 1
                identity = SourceIdentity(
                    current_file_path=normalized_file_path(source_path),
                    original_path=identity.original_path or normalized_file_path(source_path),
                    original_name=identity.original_name or source_path.name,
                    size=identity.size,
                    mtime_ns=identity.mtime_ns,
                    sha256=identity.sha256,
                    archive_member=member,
                )
                state = dict(item.state)
                state.pop("file_path", None)
                item_payloads.append(
                    {
                        "position": int(item.position),
                        "state": state,
                        "frame_number": item.frame_number,
                        "exported_at": item.exported_at,
                        "last_output": item.last_output,
                        "source": identity.to_dict(),
                    }
                )

            manifest = {
                "format": ARCHIVE_FORMAT,
                "schema_version": ARCHIVE_SCHEMA_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "project": {
                    "name": project.name,
                    "shared": dict(project.shared),
                    "current_position": current_position,
                    "output_preset": None
                    if preset is None
                    else {"name": preset.name, "settings": dict(preset.settings)},
                    "items": item_payloads,
                },
            }
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return ArchiveExportResult(
        path=output_path,
        item_count=len(item_payloads),
        bundled_original_count=bundled,
        missing_original_count=missing,
        sha256=_sha256_file(output_path),
    )


def inspect_project_archive(path: str | Path) -> ArchiveInspection:
    archive_path = Path(path).expanduser()
    manifest = _read_manifest(archive_path)
    project = _manifest_project(manifest)
    items = _manifest_items(project)
    bundled = sum(bool(SourceIdentity.from_dict(item.get("source")).archive_member) for item in items)
    missing = sum(
        not SourceIdentity.from_dict(item.get("source")).archive_member
        and not Path(SourceIdentity.from_dict(item.get("source")).original_path).is_file()
        for item in items
    )
    return ArchiveInspection(
        path=archive_path,
        project_name=str(project.get("name") or "未命名胶卷"),
        item_count=len(items),
        bundled_original_count=int(bundled),
        missing_original_count=int(missing),
        schema_version=int(manifest["schema_version"]),
    )


def import_project_archive(
    store: RollProjectStore,
    archive_path: str | Path,
    *,
    extract_originals_to: str | Path | None = None,
    project_name: str | None = None,
    make_active: bool = True,
) -> ArchiveImportResult:
    archive_file = Path(archive_path).expanduser()
    manifest = _read_manifest(archive_file)
    project = _manifest_project(manifest)
    items = _manifest_items(project)
    existing_names = {entry.name.casefold() for entry in store.list_projects()}
    desired_name = _clean_name(project_name or str(project.get("name") or "导入胶卷项目"))
    imported_name = _unique_name(desired_name, existing_names, suffix="导入")
    extraction_root = None if extract_originals_to is None else Path(extract_originals_to).expanduser()
    if any(SourceIdentity.from_dict(item.get("source")).archive_member for item in items) and extraction_root is None:
        raise ValueError("归档包含原图，请先选择原图解压目录。")

    previous_active = store.get_active_project_id()
    project_id = store.create_project(
        imported_name,
        shared=dict(project.get("shared") or {}),
        make_active=False,
    )
    states: list[dict[str, Any]] = []
    file_paths: list[Path] = []
    identities: list[SourceIdentity] = []
    extracted = 0
    missing = 0
    try:
        with zipfile.ZipFile(archive_file, "r") as archive:
            project_folder = None
            if extraction_root is not None:
                project_folder = extraction_root / _safe_component(imported_name)
                project_folder.mkdir(parents=True, exist_ok=True)
            for item in items:
                source = SourceIdentity.from_dict(item.get("source"))
                target = Path(source.original_path).expanduser() if source.original_path else Path(source.original_name)
                if source.archive_member:
                    if project_folder is None:
                        raise ValueError("归档包含原图，但没有指定解压目录。")
                    _validate_member_name(source.archive_member)
                    target = _unique_file_path(project_folder / _safe_component(source.original_name or Path(source.archive_member).name))
                    _extract_member_atomic(archive, source.archive_member, target)
                    extracted += 1
                elif not target.is_file():
                    missing += 1
                normalized_target = normalized_file_path(target)
                state = dict(item.get("state") or {})
                state["file_path"] = normalized_target
                states.append(state)
                file_paths.append(Path(normalized_target))
                identities.append(
                    SourceIdentity(
                        current_file_path=normalized_target,
                        original_path=source.original_path,
                        original_name=source.original_name or Path(normalized_target).name,
                        size=source.size,
                        mtime_ns=source.mtime_ns,
                        sha256=source.sha256,
                        archive_member=source.archive_member,
                    )
                )

        preset_id = None
        preset_payload = project.get("output_preset")
        if isinstance(preset_payload, Mapping):
            preset_names = {preset.name.casefold() for preset in store.list_output_presets()}
            preset_name = _unique_name(
                _clean_name(str(preset_payload.get("name") or f"{imported_name} 输出")),
                preset_names,
                suffix="导入",
            )
            preset_id = store.save_output_preset(
                preset_name,
                dict(preset_payload.get("settings") or {}),
            )

        current_file = None
        current_position = _optional_int(project.get("current_position"))
        if current_position is not None and 0 <= current_position < len(file_paths):
            current_file = file_paths[current_position]
        elif file_paths:
            current_file = file_paths[0]
        store.save_project(
            project_id=project_id,
            name=imported_name,
            shared=dict(project.get("shared") or {}),
            image_states=states,
            file_paths=file_paths,
            current_file=current_file,
            output_preset_id=preset_id,
        )
        save_source_identities(store, project_id, identities)
        if not make_active:
            store.set_active_project(previous_active)
    except Exception:
        store.delete_project(project_id)
        if previous_active:
            store.set_active_project(previous_active)
        raise
    return ArchiveImportResult(
        project_id=project_id,
        project_name=imported_name,
        item_count=len(file_paths),
        extracted_original_count=extracted,
        missing_original_count=missing,
    )


def relink_project_sources(
    store: RollProjectStore,
    project_id: str,
    search_roots: Sequence[str | Path],
    *,
    recursive: bool = True,
    verify_hashes_for_ambiguity: bool = True,
) -> RelinkResult:
    project = store.load_project(project_id)
    if project is None:
        raise KeyError(f"找不到胶卷项目：{project_id}")
    roots = [Path(root).expanduser() for root in search_roots]
    candidates = _index_candidate_files(roots, recursive=recursive)
    identities = load_source_identities(store, project_id)
    mappings: dict[str, str] = {}
    ambiguous = 0
    unresolved = 0
    for item in project.items:
        old_path = normalized_file_path(item.file_path)
        if Path(old_path).is_file():
            continue
        identity = identities.get(old_path) or SourceIdentity(
            current_file_path=old_path,
            original_path=old_path,
            original_name=Path(old_path).name,
            size=None,
            mtime_ns=None,
            sha256="",
        )
        matches = list(candidates.get(identity.original_name.casefold(), ()))
        if identity.size is not None:
            matches = [path for path in matches if _safe_stat_size(path) == identity.size]
        if len(matches) > 1 and identity.sha256 and verify_hashes_for_ambiguity:
            matches = [path for path in matches if _sha256_file(path) == identity.sha256]
        if len(matches) == 1:
            mappings[old_path] = normalized_file_path(matches[0])
        elif len(matches) > 1:
            ambiguous += 1
        else:
            unresolved += 1
    if mappings:
        _replace_project_paths(store, project_id, mappings)
    return RelinkResult(
        project_id=project_id,
        relinked_count=len(mappings),
        unresolved_count=unresolved,
        ambiguous_count=ambiguous,
        mappings=tuple(sorted(mappings.items())),
    )


def check_project_integrity(
    store: RollProjectStore,
    project_id: str,
    *,
    verify_hashes: bool = False,
) -> ProjectIntegrityReport:
    project = store.load_project(project_id)
    if project is None:
        raise KeyError(f"找不到胶卷项目：{project_id}")
    identities = load_source_identities(store, project_id)
    missing: list[str] = []
    changed: list[str] = []
    hash_mismatches: list[str] = []
    empty_frames: list[str] = []
    frame_map: dict[str, list[str]] = {}
    available = 0
    for item in project.items:
        key = normalized_file_path(item.file_path)
        path = Path(key)
        if not path.is_file():
            missing.append(key)
        else:
            available += 1
            identity = identities.get(key)
            if identity is not None:
                stat = path.stat()
                if identity.size is not None and stat.st_size != identity.size:
                    changed.append(key)
                elif verify_hashes and identity.sha256 and _sha256_file(path) != identity.sha256:
                    hash_mismatches.append(key)
        frame = str(item.frame_number or "").strip()
        if not frame:
            empty_frames.append(key)
        else:
            frame_map.setdefault(frame.casefold(), []).append(key)
    duplicates = tuple(
        path
        for paths in frame_map.values()
        if len(paths) > 1
        for path in paths
    )
    missing_preset = bool(
        project.output_preset_id
        and store.load_output_preset(project.output_preset_id) is None
    )
    return ProjectIntegrityReport(
        project_id=project_id,
        project_name=project.name,
        total=len(project.items),
        available=available,
        missing_paths=tuple(missing),
        changed_paths=tuple(changed),
        hash_mismatches=tuple(hash_mismatches),
        empty_frame_numbers=tuple(empty_frames),
        duplicate_frame_numbers=duplicates,
        missing_output_preset=missing_preset,
    )


def backup_project_database(store: RollProjectStore, destination: str | Path) -> Path:
    store.initialize()
    output = Path(destination).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    source = sqlite3.connect(store.path, timeout=10.0)
    target = sqlite3.connect(temporary, timeout=10.0)
    try:
        source.execute("PRAGMA busy_timeout=10000")
        with target:
            source.backup(target)
        _validate_database(temporary)
        os.replace(temporary, output)
    finally:
        target.close()
        source.close()
        temporary.unlink(missing_ok=True)
    return output


def restore_project_database(store: RollProjectStore, backup_path: str | Path) -> None:
    source_path = Path(backup_path).expanduser()
    _validate_database(source_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    temporary = store.path.with_name(f".{store.path.name}.{uuid.uuid4().hex}.restore")
    source = sqlite3.connect(source_path, timeout=10.0)
    target = sqlite3.connect(temporary, timeout=10.0)
    try:
        with target:
            source.backup(target)
        _validate_database(temporary)
        for suffix in ("-wal", "-shm"):
            Path(f"{store.path}{suffix}").unlink(missing_ok=True)
        os.replace(temporary, store.path)
    finally:
        target.close()
        source.close()
        temporary.unlink(missing_ok=True)
    store.initialize()


def load_source_identities(
    store: RollProjectStore,
    project_id: str,
) -> dict[str, SourceIdentity]:
    _ensure_source_table(store)
    with store.session() as connection:
        rows = connection.execute(
            "SELECT * FROM project_source_identities WHERE project_id = ?",
            (str(project_id),),
        ).fetchall()
    return {
        str(row["current_file_path"]): SourceIdentity(
            current_file_path=str(row["current_file_path"]),
            original_path=str(row["original_path"] or ""),
            original_name=str(row["original_name"] or ""),
            size=None if row["source_size"] is None else int(row["source_size"]),
            mtime_ns=None if row["source_mtime_ns"] is None else int(row["source_mtime_ns"]),
            sha256=str(row["source_sha256"] or ""),
            archive_member=str(row["archive_member"] or ""),
        )
        for row in rows
    }


def save_source_identities(
    store: RollProjectStore,
    project_id: str,
    identities: Iterable[SourceIdentity],
) -> None:
    _ensure_source_table(store)
    rows = [
        (
            str(project_id),
            normalized_file_path(identity.current_file_path),
            str(identity.original_path or ""),
            str(identity.original_name or ""),
            identity.size,
            identity.mtime_ns,
            str(identity.sha256 or "").lower(),
            str(identity.archive_member or ""),
        )
        for identity in identities
    ]
    with store.session() as connection:
        connection.executemany(
            """
            INSERT INTO project_source_identities(
                project_id, current_file_path, original_path, original_name,
                source_size, source_mtime_ns, source_sha256, archive_member
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, current_file_path) DO UPDATE SET
                original_path=excluded.original_path,
                original_name=excluded.original_name,
                source_size=excluded.source_size,
                source_mtime_ns=excluded.source_mtime_ns,
                source_sha256=excluded.source_sha256,
                archive_member=excluded.archive_member
            """,
            rows,
        )


def _replace_project_paths(
    store: RollProjectStore,
    project_id: str,
    mappings: Mapping[str, str],
) -> None:
    normalized_mappings = {
        normalized_file_path(old): normalized_file_path(new)
        for old, new in mappings.items()
    }
    _ensure_source_table(store)
    with store.session() as connection:
        rows = connection.execute(
            "SELECT * FROM roll_project_items WHERE project_id = ? ORDER BY position",
            (str(project_id),),
        ).fetchall()
        transformed: list[tuple[Any, ...]] = []
        final_paths: set[str] = set()
        for row in rows:
            old_path = str(row["file_path"])
            new_path = normalized_mappings.get(old_path, old_path)
            if new_path.casefold() in final_paths:
                raise ValueError(f"重新定位后出现重复文件路径：{new_path}")
            final_paths.add(new_path.casefold())
            state = dict(json.loads(row["state_json"] or "{}"))
            state["file_path"] = new_path
            transformed.append(
                (
                    str(project_id),
                    int(row["position"]),
                    new_path,
                    json.dumps(state, ensure_ascii=False, sort_keys=True),
                    str(row["frame_number"] or ""),
                    row["exported_at"],
                    row["last_output"],
                )
            )
        current_row = connection.execute(
            "SELECT current_file FROM roll_projects WHERE project_id = ?",
            (str(project_id),),
        ).fetchone()
        current_file = None if current_row is None else current_row["current_file"]
        connection.execute("DELETE FROM roll_project_items WHERE project_id = ?", (str(project_id),))
        connection.executemany(
            """
            INSERT INTO roll_project_items(
                project_id, position, file_path, state_json, frame_number,
                exported_at, last_output
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            transformed,
        )
        for old_path, new_path in normalized_mappings.items():
            connection.execute(
                """
                UPDATE project_source_identities
                SET current_file_path = ?
                WHERE project_id = ? AND current_file_path = ?
                """,
                (new_path, str(project_id), old_path),
            )
        if current_file:
            replacement = normalized_mappings.get(str(current_file), str(current_file))
            connection.execute(
                "UPDATE roll_projects SET current_file = ?, updated_at = ? WHERE project_id = ?",
                (replacement, int(time.time()), str(project_id)),
            )


def _ensure_source_table(store: RollProjectStore) -> None:
    store.initialize()
    with store.session() as connection:
        connection.executescript(SOURCE_TABLE_SQL)


def _identity_for_export(
    path: Path,
    stored: SourceIdentity | None,
    *,
    calculate_hash: bool,
) -> SourceIdentity:
    if not path.is_file():
        return stored or SourceIdentity(
            current_file_path=normalized_file_path(path),
            original_path=normalized_file_path(path),
            original_name=path.name,
            size=None,
            mtime_ns=None,
            sha256="",
        )
    stat = path.stat()
    sha256 = _sha256_file(path) if calculate_hash else (stored.sha256 if stored else "")
    return SourceIdentity(
        current_file_path=normalized_file_path(path),
        original_path=(stored.original_path if stored else normalized_file_path(path)),
        original_name=(stored.original_name if stored else path.name),
        size=int(stat.st_size),
        mtime_ns=int(stat.st_mtime_ns),
        sha256=sha256,
        archive_member=(stored.archive_member if stored else ""),
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"找不到项目归档：{path}")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for name in archive.namelist():
                _validate_member_name(name)
            payload = archive.read(MANIFEST_NAME)
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("不是有效的 PS-Sezhao 项目归档。") from exc
    try:
        manifest = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("项目归档清单损坏。") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != ARCHIVE_FORMAT:
        raise ValueError("项目归档格式不受支持。")
    version = _optional_int(manifest.get("schema_version"))
    if version != ARCHIVE_SCHEMA_VERSION:
        raise ValueError(f"不支持的项目归档版本：{version}")
    _manifest_project(manifest)
    return manifest


def _manifest_project(manifest: Mapping[str, Any]) -> dict[str, Any]:
    project = manifest.get("project")
    if not isinstance(project, dict):
        raise ValueError("项目归档缺少 project 清单。")
    _manifest_items(project)
    return project


def _manifest_items(project: Mapping[str, Any]) -> list[dict[str, Any]]:
    items = project.get("items")
    if not isinstance(items, list):
        raise ValueError("项目归档缺少图片清单。")
    normalized: list[dict[str, Any]] = []
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"项目归档第 {position + 1} 个图片记录无效。")
        source = SourceIdentity.from_dict(item.get("source"))
        if source.archive_member:
            _validate_member_name(source.archive_member)
        normalized.append(item)
    return normalized


def _validate_member_name(name: str) -> None:
    path = PurePosixPath(str(name))
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"项目归档包含不安全路径：{name}")


def _extract_member_atomic(archive: zipfile.ZipFile, member: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with archive.open(member, "r") as source, temporary.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _validate_database(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"找不到数据库备份：{path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10.0)
    try:
        result = connection.execute("PRAGMA quick_check").fetchone()
        if result is None or str(result[0]).lower() != "ok":
            raise ValueError(f"数据库完整性检查失败：{result[0] if result else 'unknown'}")
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        required = {"metadata", "roll_projects", "roll_project_items", "output_presets"}
        missing = required - tables
        if missing:
            raise ValueError(f"数据库备份缺少表：{', '.join(sorted(missing))}")
    finally:
        connection.close()


def _index_candidate_files(
    roots: Sequence[Path],
    *,
    recursive: bool,
) -> dict[str, tuple[Path, ...]]:
    result: dict[str, list[Path]] = {}
    for root in roots:
        if root.is_file():
            result.setdefault(root.name.casefold(), []).append(root)
            continue
        if not root.is_dir():
            continue
        iterator = root.rglob("*") if recursive else root.glob("*")
        for path in iterator:
            if path.is_file():
                result.setdefault(path.name.casefold(), []).append(path)
    return {name: tuple(paths) for name, paths in result.items()}


def _archive_destination(path: str | Path) -> Path:
    destination = Path(path).expanduser()
    if destination.suffix.lower() != ARCHIVE_SUFFIX:
        destination = destination.with_suffix(ARCHIVE_SUFFIX)
    return destination


def _original_member(position: int, name: str) -> str:
    return f"originals/{int(position):05d}_{_safe_component(name)}"


def _safe_component(value: str) -> str:
    cleaned = "".join("_" if char in '<>:"/\\|?*\x00' else char for char in str(value or ""))
    cleaned = " ".join(cleaned.split()).strip(" .")
    return cleaned[:180] or "untitled"


def _clean_name(value: str) -> str:
    cleaned = " ".join(str(value or "").replace("\x00", " ").split())[:160]
    if not cleaned:
        raise ValueError("项目名称不能为空。")
    return cleaned


def _unique_name(base: str, existing_casefold: set[str], *, suffix: str) -> str:
    if base.casefold() not in existing_casefold:
        return base
    candidate = f"{base}（{suffix}）"
    if candidate.casefold() not in existing_casefold:
        return candidate
    index = 2
    while True:
        candidate = f"{base}（{suffix} {index}）"
        if candidate.casefold() not in existing_casefold:
            return candidate
        index += 1


def _unique_file_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 100000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"无法为文件生成不重复名称：{path}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _safe_stat_size(path: Path) -> int | None:
    try:
        return int(path.stat().st_size)
    except OSError:
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

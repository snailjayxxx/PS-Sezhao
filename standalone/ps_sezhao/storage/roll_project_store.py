from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from ..core.roll_project import RollProjectSettings
from .project_store import normalized_file_path


ROLL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS roll_projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    shared_json TEXT NOT NULL DEFAULT '{}',
    current_file TEXT,
    output_preset_id TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS roll_project_items (
    project_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    state_json TEXT NOT NULL,
    frame_number TEXT NOT NULL DEFAULT '',
    exported_at INTEGER,
    last_output TEXT,
    PRIMARY KEY(project_id, file_path),
    UNIQUE(project_id, position),
    FOREIGN KEY(project_id) REFERENCES roll_projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_roll_project_items_position
ON roll_project_items(project_id, position);

CREATE TABLE IF NOT EXISTS output_presets (
    preset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    settings_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class StoredRollItem:
    file_path: str
    position: int
    state: dict[str, Any]
    frame_number: str
    exported_at: int | None
    last_output: str | None


@dataclass(frozen=True)
class StoredRollProject:
    project_id: str
    name: str
    shared: dict[str, Any]
    current_file: str | None
    output_preset_id: str | None
    created_at: int
    updated_at: int
    items: tuple[StoredRollItem, ...]

    @property
    def exported_paths(self) -> tuple[str, ...]:
        return tuple(item.file_path for item in self.items if item.exported_at is not None)


@dataclass(frozen=True)
class RollProjectListItem:
    project_id: str
    name: str
    shared: dict[str, Any]
    item_count: int
    exported_count: int
    updated_at: int


@dataclass(frozen=True)
class StoredOutputPreset:
    preset_id: str
    name: str
    settings: dict[str, Any]
    created_at: int
    updated_at: int


class RollProjectStore:
    """Multiple recoverable roll projects stored in the standalone SQLite database."""

    ACTIVE_PROJECT_KEY = "active_roll_project_id"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.session() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.executescript(ROLL_SCHEMA_SQL)

    def create_project(
        self,
        name: str,
        *,
        shared: Mapping[str, Any] | None = None,
        project_id: str | None = None,
        make_active: bool = True,
    ) -> str:
        self.initialize()
        identifier = str(project_id or uuid.uuid4().hex)
        timestamp = int(time.time())
        cleaned_name = _clean_name(name)
        settings = RollProjectSettings.from_dict(shared).to_dict()
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO roll_projects(
                    project_id, name, shared_json, current_file, output_preset_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    identifier,
                    cleaned_name,
                    json.dumps(settings, ensure_ascii=False, sort_keys=True),
                    timestamp,
                    timestamp,
                ),
            )
            if make_active:
                self._set_metadata(connection, self.ACTIVE_PROJECT_KEY, identifier)
        return identifier

    def save_project(
        self,
        *,
        project_id: str,
        name: str,
        shared: Mapping[str, Any] | None,
        image_states: Iterable[Mapping[str, Any]],
        file_paths: Iterable[str | Path],
        current_file: str | Path | None,
        output_preset_id: str | None = None,
        updated_at: int | None = None,
    ) -> None:
        self.initialize()
        timestamp = int(time.time()) if updated_at is None else int(updated_at)
        settings = RollProjectSettings.from_dict(shared).to_dict()
        ordered_paths = [normalized_file_path(path) for path in file_paths]
        states_by_path = {
            normalized_file_path(state["file_path"]): _normalized_state(state)
            for state in image_states
        }
        with self.session() as connection:
            existing = {
                str(row["file_path"]): (
                    row["exported_at"],
                    row["last_output"],
                )
                for row in connection.execute(
                    "SELECT file_path, exported_at, last_output FROM roll_project_items WHERE project_id = ?",
                    (str(project_id),),
                ).fetchall()
            }
            created_row = connection.execute(
                "SELECT created_at FROM roll_projects WHERE project_id = ?",
                (str(project_id),),
            ).fetchone()
            created_at = timestamp if created_row is None else int(created_row["created_at"])
            connection.execute(
                """
                INSERT INTO roll_projects(
                    project_id, name, shared_json, current_file, output_preset_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    name=excluded.name,
                    shared_json=excluded.shared_json,
                    current_file=excluded.current_file,
                    output_preset_id=excluded.output_preset_id,
                    updated_at=excluded.updated_at
                """,
                (
                    str(project_id),
                    _clean_name(name),
                    json.dumps(settings, ensure_ascii=False, sort_keys=True),
                    None if current_file is None else normalized_file_path(current_file),
                    str(output_preset_id) if output_preset_id else None,
                    created_at,
                    timestamp,
                ),
            )
            connection.execute("DELETE FROM roll_project_items WHERE project_id = ?", (str(project_id),))
            rows: list[tuple[Any, ...]] = []
            for position, path in enumerate(ordered_paths):
                state = states_by_path.get(path, _normalized_state({"file_path": path}))
                output = dict(state.get("output_settings") or {})
                exported_at, last_output = existing.get(path, (None, None))
                rows.append(
                    (
                        str(project_id),
                        position,
                        path,
                        json.dumps(state, ensure_ascii=False, sort_keys=True),
                        str(output.get("frame_number") or ""),
                        exported_at,
                        last_output,
                    )
                )
            connection.executemany(
                """
                INSERT INTO roll_project_items(
                    project_id, position, file_path, state_json, frame_number,
                    exported_at, last_output
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self._set_metadata(connection, self.ACTIVE_PROJECT_KEY, str(project_id))

    def load_project(self, project_id: str) -> StoredRollProject | None:
        self.initialize()
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM roll_projects WHERE project_id = ?",
                (str(project_id),),
            ).fetchone()
            if row is None:
                return None
            item_rows = connection.execute(
                "SELECT * FROM roll_project_items WHERE project_id = ? ORDER BY position",
                (str(project_id),),
            ).fetchall()
        items = tuple(
            StoredRollItem(
                file_path=str(item["file_path"]),
                position=int(item["position"]),
                state=dict(json.loads(item["state_json"] or "{}")),
                frame_number=str(item["frame_number"] or ""),
                exported_at=None if item["exported_at"] is None else int(item["exported_at"]),
                last_output=None if item["last_output"] is None else str(item["last_output"]),
            )
            for item in item_rows
        )
        return StoredRollProject(
            project_id=str(row["project_id"]),
            name=str(row["name"]),
            shared=dict(json.loads(row["shared_json"] or "{}")),
            current_file=None if not row["current_file"] else str(row["current_file"]),
            output_preset_id=None if not row["output_preset_id"] else str(row["output_preset_id"]),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
            items=items,
        )

    def list_projects(self) -> tuple[RollProjectListItem, ...]:
        self.initialize()
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.project_id,
                    p.name,
                    p.shared_json,
                    p.updated_at,
                    COUNT(i.file_path) AS item_count,
                    SUM(CASE WHEN i.exported_at IS NOT NULL THEN 1 ELSE 0 END) AS exported_count
                FROM roll_projects p
                LEFT JOIN roll_project_items i ON i.project_id = p.project_id
                GROUP BY p.project_id
                ORDER BY p.updated_at DESC, p.name COLLATE NOCASE
                """
            ).fetchall()
        return tuple(
            RollProjectListItem(
                project_id=str(row["project_id"]),
                name=str(row["name"]),
                shared=dict(json.loads(row["shared_json"] or "{}")),
                item_count=int(row["item_count"] or 0),
                exported_count=int(row["exported_count"] or 0),
                updated_at=int(row["updated_at"]),
            )
            for row in rows
        )

    def delete_project(self, project_id: str) -> None:
        self.initialize()
        with self.session() as connection:
            connection.execute("DELETE FROM roll_projects WHERE project_id = ?", (str(project_id),))
            active = self._get_metadata(connection, self.ACTIVE_PROJECT_KEY)
            if active == str(project_id):
                self._set_metadata(connection, self.ACTIVE_PROJECT_KEY, "")

    def get_active_project_id(self) -> str | None:
        self.initialize()
        with self.session() as connection:
            value = self._get_metadata(connection, self.ACTIVE_PROJECT_KEY)
        return value or None

    def set_active_project(self, project_id: str | None) -> None:
        self.initialize()
        with self.session() as connection:
            if project_id:
                exists = connection.execute(
                    "SELECT 1 FROM roll_projects WHERE project_id = ?",
                    (str(project_id),),
                ).fetchone()
                if exists is None:
                    raise KeyError(f"找不到胶卷项目：{project_id}")
            self._set_metadata(connection, self.ACTIVE_PROJECT_KEY, str(project_id or ""))

    def mark_exported(
        self,
        project_id: str,
        source: str | Path,
        destination: str | Path,
        *,
        exported_at: int | None = None,
    ) -> None:
        self.initialize()
        timestamp = int(time.time()) if exported_at is None else int(exported_at)
        with self.session() as connection:
            connection.execute(
                """
                UPDATE roll_project_items
                SET exported_at = ?, last_output = ?
                WHERE project_id = ? AND file_path = ?
                """,
                (
                    timestamp,
                    normalized_file_path(destination),
                    str(project_id),
                    normalized_file_path(source),
                ),
            )
            connection.execute(
                "UPDATE roll_projects SET updated_at = ? WHERE project_id = ?",
                (timestamp, str(project_id)),
            )

    def save_output_preset(
        self,
        name: str,
        settings: Mapping[str, Any],
        *,
        preset_id: str | None = None,
    ) -> str:
        self.initialize()
        identifier = str(preset_id or uuid.uuid4().hex)
        timestamp = int(time.time())
        cleaned_name = _clean_name(name)
        payload = json.dumps(dict(settings), ensure_ascii=False, sort_keys=True)
        with self.session() as connection:
            row = connection.execute(
                "SELECT preset_id, created_at FROM output_presets WHERE name = ? COLLATE NOCASE",
                (cleaned_name,),
            ).fetchone()
            if row is not None and preset_id is None:
                identifier = str(row["preset_id"])
                created_at = int(row["created_at"])
            else:
                created_at = timestamp
            connection.execute(
                """
                INSERT INTO output_presets(
                    preset_id, name, settings_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(preset_id) DO UPDATE SET
                    name=excluded.name,
                    settings_json=excluded.settings_json,
                    updated_at=excluded.updated_at
                """,
                (identifier, cleaned_name, payload, created_at, timestamp),
            )
        return identifier

    def list_output_presets(self) -> tuple[StoredOutputPreset, ...]:
        self.initialize()
        with self.session() as connection:
            rows = connection.execute(
                "SELECT * FROM output_presets ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return tuple(_preset_from_row(row) for row in rows)

    def load_output_preset(self, preset_id: str) -> StoredOutputPreset | None:
        self.initialize()
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM output_presets WHERE preset_id = ?",
                (str(preset_id),),
            ).fetchone()
        return None if row is None else _preset_from_row(row)

    def delete_output_preset(self, preset_id: str) -> None:
        self.initialize()
        with self.session() as connection:
            connection.execute("DELETE FROM output_presets WHERE preset_id = ?", (str(preset_id),))
            connection.execute(
                "UPDATE roll_projects SET output_preset_id = NULL WHERE output_preset_id = ?",
                (str(preset_id),),
            )

    @staticmethod
    def _set_metadata(connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            "INSERT INTO metadata(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(key), str(value)),
        )

    @staticmethod
    def _get_metadata(connection: sqlite3.Connection, key: str) -> str | None:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (str(key),),
        ).fetchone()
        return None if row is None else str(row["value"])


def _normalized_state(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "file_path": normalized_file_path(state.get("file_path") or ""),
        "controls": dict(state.get("controls") or {}),
        "analysis": None if state.get("analysis") is None else dict(state.get("analysis") or {}),
        "crop": [float(value) for value in (state.get("crop") or (0.0, 0.0, 1.0, 1.0))],
        "rotation": int(state.get("rotation") or 0) % 360,
        "geometry": dict(state.get("geometry") or {}),
        "raw_settings": dict(state.get("raw_settings") or {}),
        "output_settings": dict(state.get("output_settings") or {}),
    }


def _preset_from_row(row: sqlite3.Row) -> StoredOutputPreset:
    return StoredOutputPreset(
        preset_id=str(row["preset_id"]),
        name=str(row["name"]),
        settings=dict(json.loads(row["settings_json"] or "{}")),
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


def _clean_name(value: Any) -> str:
    cleaned = " ".join(str(value or "").replace("\x00", " ").split())[:160]
    if not cleaned:
        raise ValueError("名称不能为空。")
    return cleaned

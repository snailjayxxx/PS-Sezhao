from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from pathlib import Path


ENV_PROJECT_DATABASE = "PS_SEZHAO_PROJECT_DB"
ENV_DATA_ROOT = "PS_SEZHAO_DATA_ROOT"
PORTABLE_MARKER = ".ps-sezhao-portable"
PROJECT_DIRECTORY_NAME = "project"
LUT_DIRECTORY_NAME = "lut"
DATABASE_FILENAME = "workspace.sqlite3"


def application_container() -> Path:
    """Return the directory that contains the packaged app or executable."""

    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).expanduser().resolve(strict=False)
        if sys.platform == "darwin":
            for parent in executable.parents:
                if parent.suffix.lower() == ".app":
                    return parent.parent
        return executable.parent

    # Source runs use the repository root as the portable container.  The file
    # lives at standalone/ps_sezhao/storage/paths.py.
    return Path(__file__).resolve(strict=False).parents[3]


def _legacy_data_root() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "PS-Sezhao"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
        return base / "PS-Sezhao"
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else home / ".local" / "state"
    return base / "PS-Sezhao"


def legacy_project_database_path() -> Path:
    return _legacy_data_root() / DATABASE_FILENAME


def _fallback_data_root() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        # A lone .app copied directly into /Applications cannot safely create
        # sibling folders there. Keep user-visible projects in Documents.
        return home / "Documents" / "PS-Sezhao"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
        return base / "PS-Sezhao"
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else home / ".local" / "share"
    return base / "PS-Sezhao"


def _root_is_writable(root: Path) -> bool:
    probe = root if root.exists() else root.parent
    try:
        return probe.exists() and os.access(probe, os.W_OK)
    except OSError:
        return False


def _portable_layout_present(root: Path) -> bool:
    return any(
        (
            (root / PORTABLE_MARKER).exists(),
            (root / PROJECT_DIRECTORY_NAME).is_dir(),
            (root / LUT_DIRECTORY_NAME).is_dir(),
        )
    )


def default_data_root() -> Path:
    """Resolve the writable root shared by the app, project and LUT folders."""

    override = os.environ.get(ENV_DATA_ROOT)
    if override:
        return Path(override).expanduser().resolve(strict=False)

    container = application_container()
    source_run = not getattr(sys, "frozen", False)
    if _root_is_writable(container) and (source_run or _portable_layout_present(container)):
        return container
    return _fallback_data_root()


def ensure_data_layout() -> Path:
    root = default_data_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / PROJECT_DIRECTORY_NAME).mkdir(parents=True, exist_ok=True)
    (root / LUT_DIRECTORY_NAME).mkdir(parents=True, exist_ok=True)
    marker = root / PORTABLE_MARKER
    if not marker.exists():
        try:
            marker.write_text(
                "PS-Sezhao portable data root. Keep project and lut beside the application.\n",
                encoding="utf-8",
            )
        except OSError:
            pass
    return root


def default_project_directory() -> Path:
    return ensure_data_layout() / PROJECT_DIRECTORY_NAME


def default_lut_directory() -> Path:
    return ensure_data_layout() / LUT_DIRECTORY_NAME


def _migrate_legacy_database(target: Path) -> None:
    legacy = legacy_project_database_path()
    if target.exists() or not legacy.is_file():
        return
    try:
        if legacy.resolve(strict=False) == target.resolve(strict=False):
            return
    except OSError:
        pass

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".migrating")
    try:
        temporary.unlink(missing_ok=True)
        with sqlite3.connect(legacy) as source, sqlite3.connect(temporary) as destination:
            source.backup(destination)
        temporary.replace(target)
        note = target.parent / "MIGRATED_FROM.txt"
        note.write_text(
            "PS-Sezhao automatically migrated the previous project database from:\n"
            f"{legacy}\n\n"
            "The previous file was intentionally retained as a safety backup.\n",
            encoding="utf-8",
        )
    except Exception:
        temporary.unlink(missing_ok=True)
        try:
            shutil.copy2(legacy, target)
        except OSError:
            target.unlink(missing_ok=True)


def default_project_database_path() -> Path:
    """Return the portable project database and migrate the previous location."""

    override = os.environ.get(ENV_PROJECT_DATABASE)
    if override:
        return Path(override).expanduser().resolve(strict=False)

    target = default_project_directory() / DATABASE_FILENAME
    _migrate_legacy_database(target)
    return target

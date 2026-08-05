from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

from .roll_project_store import RollProjectStore


REQUIRED_TABLES = {
    "metadata",
    "roll_projects",
    "roll_project_items",
    "output_presets",
}


def backup_project_database(store: RollProjectStore, destination: str | Path) -> Path:
    """Create a consistent online SQLite backup and atomically publish it."""

    store.initialize()
    output = Path(destination).expanduser().resolve(strict=False)
    source_path = store.path.expanduser().resolve(strict=False)
    if output == source_path:
        raise ValueError("数据库备份位置不能与当前数据库相同。")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    source: sqlite3.Connection | None = None
    target: sqlite3.Connection | None = None
    try:
        source = sqlite3.connect(source_path, timeout=10.0)
        target = sqlite3.connect(temporary, timeout=10.0)
        source.execute("PRAGMA busy_timeout=10000")
        target.execute("PRAGMA busy_timeout=10000")
        source.backup(target)
        target.commit()
    finally:
        if target is not None:
            target.close()
        if source is not None:
            source.close()
    try:
        validate_project_database(temporary)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def restore_project_database(store: RollProjectStore, backup_path: str | Path) -> None:
    """Validate and atomically restore a database after all handles are closed."""

    source_path = Path(backup_path).expanduser().resolve(strict=False)
    destination = store.path.expanduser().resolve(strict=False)
    if source_path == destination:
        raise ValueError("恢复来源不能是当前正在使用的数据库。")
    validate_project_database(source_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.restore")
    source: sqlite3.Connection | None = None
    target: sqlite3.Connection | None = None
    try:
        source = sqlite3.connect(source_path, timeout=10.0)
        target = sqlite3.connect(temporary, timeout=10.0)
        source.execute("PRAGMA busy_timeout=10000")
        target.execute("PRAGMA busy_timeout=10000")
        source.backup(target)
        target.commit()
    finally:
        if target is not None:
            target.close()
        if source is not None:
            source.close()
    try:
        validate_project_database(temporary)
        for suffix in ("-wal", "-shm"):
            Path(f"{destination}{suffix}").unlink(missing_ok=True)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    store.initialize()


def validate_project_database(path: str | Path) -> None:
    database = Path(path).expanduser()
    if not database.is_file():
        raise FileNotFoundError(f"找不到数据库备份：{database}")
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=10.0)
    try:
        row = connection.execute("PRAGMA quick_check").fetchone()
        if row is None or str(row[0]).lower() != "ok":
            raise ValueError(f"数据库完整性检查失败：{row[0] if row else 'unknown'}")
        tables = {
            str(item[0])
            for item in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError(f"数据库备份缺少表：{', '.join(sorted(missing))}")
    finally:
        connection.close()

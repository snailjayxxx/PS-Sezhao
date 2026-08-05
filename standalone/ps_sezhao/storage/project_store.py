from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from ..core.contracts import (
    MATH_CONTRACT_VERSION,
    PROJECT_SCHEMA_VERSION,
    RAW_DECODE_CONTRACT_VERSION,
)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_states (
    file_path TEXT PRIMARY KEY,
    controls_json TEXT NOT NULL,
    analysis_json TEXT,
    crop_json TEXT NOT NULL,
    rotation INTEGER NOT NULL DEFAULT 0,
    geometry_json TEXT NOT NULL DEFAULT '{}',
    raw_settings_json TEXT NOT NULL DEFAULT '{}',
    output_settings_json TEXT NOT NULL DEFAULT '{}',
    math_version INTEGER NOT NULL,
    raw_decode_version INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_items (
    position INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE
);
"""


@dataclass(frozen=True)
class StoredImageState:
    file_path: str
    controls: dict[str, Any]
    analysis: dict[str, Any] | None
    crop: tuple[float, float, float, float]
    rotation: int
    geometry: dict[str, Any]
    raw_settings: dict[str, Any]
    output_settings: dict[str, Any]
    math_version: int
    raw_decode_version: int
    updated_at: int


@dataclass(frozen=True)
class StoredWorkspace:
    file_paths: tuple[str, ...]
    current_file: str | None


def normalized_file_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve(strict=False))


class ProjectStore:
    """Versioned SQLite storage for the recoverable standalone workspace."""

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
            connection.executescript(SCHEMA_SQL)
            self._ensure_image_state_columns(connection)
            self._set_metadata(connection, "schema_version", str(PROJECT_SCHEMA_VERSION))

    def _ensure_image_state_columns(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(image_states)").fetchall()
        }
        additions = {
            "geometry_json": "TEXT NOT NULL DEFAULT '{}'",
            "raw_settings_json": "TEXT NOT NULL DEFAULT '{}'",
            "output_settings_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE image_states ADD COLUMN {name} {definition}")

    def _set_metadata(self, connection: sqlite3.Connection, key: str, value: str) -> None:
        connection.execute(
            "INSERT INTO metadata(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(key), str(value)),
        )

    def _get_metadata(self, connection: sqlite3.Connection, key: str) -> str | None:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (str(key),),
        ).fetchone()
        return None if row is None else str(row["value"])

    def _upsert_image_state(
        self,
        connection: sqlite3.Connection,
        *,
        file_path: str | Path,
        controls: Mapping[str, Any],
        analysis: Mapping[str, Any] | None,
        crop: Iterable[float],
        rotation: int,
        geometry: Mapping[str, Any] | None,
        raw_settings: Mapping[str, Any] | None,
        output_settings: Mapping[str, Any] | None,
        updated_at: int,
    ) -> None:
        normalized_crop = tuple(float(value) for value in crop)
        if len(normalized_crop) != 4:
            raise ValueError("crop must contain four normalized values")

        connection.execute(
            """
            INSERT INTO image_states(
                file_path,
                controls_json,
                analysis_json,
                crop_json,
                rotation,
                geometry_json,
                raw_settings_json,
                output_settings_json,
                math_version,
                raw_decode_version,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                controls_json=excluded.controls_json,
                analysis_json=excluded.analysis_json,
                crop_json=excluded.crop_json,
                rotation=excluded.rotation,
                geometry_json=excluded.geometry_json,
                raw_settings_json=excluded.raw_settings_json,
                output_settings_json=excluded.output_settings_json,
                math_version=excluded.math_version,
                raw_decode_version=excluded.raw_decode_version,
                updated_at=excluded.updated_at
            """,
            (
                normalized_file_path(file_path),
                json.dumps(dict(controls), ensure_ascii=False, sort_keys=True),
                None
                if analysis is None
                else json.dumps(dict(analysis), ensure_ascii=False, sort_keys=True),
                json.dumps(normalized_crop),
                int(rotation) % 360,
                json.dumps(dict(geometry or {}), ensure_ascii=False, sort_keys=True),
                json.dumps(dict(raw_settings or {}), ensure_ascii=False, sort_keys=True),
                json.dumps(dict(output_settings or {}), ensure_ascii=False, sort_keys=True),
                MATH_CONTRACT_VERSION,
                RAW_DECODE_CONTRACT_VERSION,
                int(updated_at),
            ),
        )

    def save_image_state(
        self,
        *,
        file_path: str | Path,
        controls: Mapping[str, Any],
        analysis: Mapping[str, Any] | None,
        crop: Iterable[float],
        rotation: int,
        geometry: Mapping[str, Any] | None = None,
        raw_settings: Mapping[str, Any] | None = None,
        output_settings: Mapping[str, Any] | None = None,
        updated_at: int | None = None,
    ) -> None:
        self.initialize()
        timestamp = int(time.time()) if updated_at is None else int(updated_at)
        with self.session() as connection:
            self._upsert_image_state(
                connection,
                file_path=file_path,
                controls=controls,
                analysis=analysis,
                crop=crop,
                rotation=rotation,
                geometry=geometry,
                raw_settings=raw_settings,
                output_settings=output_settings,
                updated_at=timestamp,
            )

    def save_session(
        self,
        *,
        image_states: Iterable[Mapping[str, Any]],
        file_paths: Iterable[str | Path],
        current_file: str | Path | None,
        updated_at: int | None = None,
    ) -> None:
        """Atomically save list order, active file and all image edit states."""

        self.initialize()
        timestamp = int(time.time()) if updated_at is None else int(updated_at)
        ordered_paths = [normalized_file_path(path) for path in file_paths]
        with self.session() as connection:
            connection.execute("DELETE FROM workspace_items")
            connection.executemany(
                "INSERT INTO workspace_items(position, file_path) VALUES(?, ?)",
                [(position, path) for position, path in enumerate(ordered_paths)],
            )
            self._set_metadata(
                connection,
                "current_file",
                "" if current_file is None else normalized_file_path(current_file),
            )
            for state in image_states:
                self._upsert_image_state(
                    connection,
                    file_path=state["file_path"],
                    controls=state.get("controls") or {},
                    analysis=state.get("analysis"),
                    crop=state.get("crop") or (0.0, 0.0, 1.0, 1.0),
                    rotation=int(state.get("rotation") or 0),
                    geometry=state.get("geometry") or {},
                    raw_settings=state.get("raw_settings") or {},
                    output_settings=state.get("output_settings") or {},
                    updated_at=timestamp,
                )

    def load_image_state(self, file_path: str | Path) -> StoredImageState | None:
        self.initialize()
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM image_states WHERE file_path = ?",
                (normalized_file_path(file_path),),
            ).fetchone()
        if row is None:
            return None

        crop = tuple(float(value) for value in json.loads(row["crop_json"]))
        if len(crop) != 4:
            raise ValueError("stored crop must contain four normalized values")
        analysis_payload = row["analysis_json"]
        return StoredImageState(
            file_path=str(row["file_path"]),
            controls=dict(json.loads(row["controls_json"])),
            analysis=None if analysis_payload is None else dict(json.loads(analysis_payload)),
            crop=(crop[0], crop[1], crop[2], crop[3]),
            rotation=int(row["rotation"]),
            geometry=dict(json.loads(row["geometry_json"] or "{}")),
            raw_settings=dict(json.loads(row["raw_settings_json"] or "{}")),
            output_settings=dict(json.loads(row["output_settings_json"] or "{}")),
            math_version=int(row["math_version"]),
            raw_decode_version=int(row["raw_decode_version"]),
            updated_at=int(row["updated_at"]),
        )

    def load_workspace(self) -> StoredWorkspace:
        self.initialize()
        with self.session() as connection:
            rows = connection.execute(
                "SELECT file_path FROM workspace_items ORDER BY position"
            ).fetchall()
            current_file = self._get_metadata(connection, "current_file")
        return StoredWorkspace(
            file_paths=tuple(str(row["file_path"]) for row in rows),
            current_file=current_file or None,
        )

    def clear_workspace(self) -> None:
        self.initialize()
        with self.session() as connection:
            connection.execute("DELETE FROM workspace_items")
            self._set_metadata(connection, "current_file", "")

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

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
    math_version INTEGER NOT NULL,
    raw_decode_version INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class StoredImageState:
    file_path: str
    controls: dict[str, Any]
    analysis: dict[str, Any] | None
    crop: tuple[float, float, float, float]
    rotation: int
    math_version: int
    raw_decode_version: int
    updated_at: int


class ProjectStore:
    """Small versioned SQLite boundary for future persistent projects."""

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

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            connection.execute(
                "INSERT INTO metadata(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(PROJECT_SCHEMA_VERSION),),
            )

    def save_image_state(
        self,
        *,
        file_path: str | Path,
        controls: Mapping[str, Any],
        analysis: Mapping[str, Any] | None,
        crop: tuple[float, float, float, float],
        rotation: int,
        updated_at: int | None = None,
    ) -> None:
        self.initialize()
        timestamp = int(time.time()) if updated_at is None else int(updated_at)
        normalized_crop = tuple(float(value) for value in crop)
        if len(normalized_crop) != 4:
            raise ValueError("crop must contain four normalized values")

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO image_states(
                    file_path,
                    controls_json,
                    analysis_json,
                    crop_json,
                    rotation,
                    math_version,
                    raw_decode_version,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    controls_json=excluded.controls_json,
                    analysis_json=excluded.analysis_json,
                    crop_json=excluded.crop_json,
                    rotation=excluded.rotation,
                    math_version=excluded.math_version,
                    raw_decode_version=excluded.raw_decode_version,
                    updated_at=excluded.updated_at
                """,
                (
                    str(Path(file_path)),
                    json.dumps(dict(controls), ensure_ascii=False, sort_keys=True),
                    None
                    if analysis is None
                    else json.dumps(dict(analysis), ensure_ascii=False, sort_keys=True),
                    json.dumps(normalized_crop),
                    int(rotation) % 360,
                    MATH_CONTRACT_VERSION,
                    RAW_DECODE_CONTRACT_VERSION,
                    timestamp,
                ),
            )

    def load_image_state(self, file_path: str | Path) -> StoredImageState | None:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM image_states WHERE file_path = ?",
                (str(Path(file_path)),),
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
            math_version=int(row["math_version"]),
            raw_decode_version=int(row["raw_decode_version"]),
            updated_at=int(row["updated_at"]),
        )

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ps_sezhao.bootstrap import integration_steps
from ps_sezhao.storage.database_backup import (
    backup_project_database,
    restore_project_database,
    validate_project_database,
)
from ps_sezhao.storage.roll_project_store import RollProjectStore


class DatabaseBackupV070Tests(unittest.TestCase):
    def test_backup_and_restore_use_valid_closed_database_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = RollProjectStore(root / "workspace.sqlite3")
            project_id = store.create_project("Backup Roll")
            store.save_project(
                project_id=project_id,
                name="Backup Roll",
                shared={},
                image_states=[],
                file_paths=[],
                current_file=None,
            )
            backup = backup_project_database(store, root / "backup.sqlite3")
            validate_project_database(backup)
            store.delete_project(project_id)
            self.assertIsNone(store.load_project(project_id))
            restore_project_database(store, backup)
            self.assertIsNotNone(store.load_project(project_id))

    def test_same_database_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RollProjectStore(Path(directory) / "workspace.sqlite3")
            store.initialize()
            with self.assertRaises(ValueError):
                backup_project_database(store, store.path)
            with self.assertRaises(ValueError):
                restore_project_database(store, store.path)

    def test_invalid_sqlite_file_is_rejected_before_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / "invalid.sqlite3"
            connection = sqlite3.connect(invalid)
            try:
                connection.execute("CREATE TABLE unrelated(value TEXT)")
                connection.commit()
            finally:
                connection.close()
            with self.assertRaises(ValueError):
                validate_project_database(invalid)

    def test_archive_platform_guard_is_inside_persistence_group_before_facade(self) -> None:
        names = tuple(step.name for step in integration_steps())
        self.assertLess(names.index("services.persistence"), names.index("lifecycle.facade"))
        root = Path(__file__).resolve().parents[2]
        source = (root / "standalone/ps_sezhao/integration_groups.py").read_text(encoding="utf-8")
        self.assertLess(
            source.index("apply_project_archive_pipeline(app_class)"),
            source.index("apply_project_archive_platform_guard(app_class)"),
        )


if __name__ == "__main__":
    unittest.main()

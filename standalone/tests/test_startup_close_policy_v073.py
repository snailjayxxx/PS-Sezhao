from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from ps_sezhao.storage.project_store import ProjectStore
from ps_sezhao.storage.roll_project_store import RollProjectStore
from ps_sezhao.ui import create_application, create_root


class StartupClosePolicyTests(unittest.TestCase):
    def _create_image(self, directory: Path) -> Path:
        path = directory / "negative.png"
        Image.new("RGB", (80, 60), (210, 130, 70)).save(path)
        return path

    def test_cancel_close_keeps_window_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root_path = Path(directory)
            database = root_path / "workspace.sqlite3"
            image_path = self._create_image(root_path)
            with patch.dict(os.environ, {"PS_SEZHAO_PROJECT_DB": str(database)}):
                root = create_root()
                root.withdraw()
                try:
                    app = create_application(root, initial_files=[str(image_path)])
                    root.update_idletasks()
                    with patch(
                        "ps_sezhao.services.startup_close_policy.messagebox.askyesnocancel",
                        return_value=None,
                    ):
                        app._close_with_project_prompt()
                    self.assertEqual(root.winfo_exists(), 1)
                    self.assertEqual(len(app.items), 1)
                finally:
                    if root.winfo_exists():
                        root.destroy()

    def test_close_without_saving_clears_transient_photo_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root_path = Path(directory)
            database = root_path / "workspace.sqlite3"
            image_path = self._create_image(root_path)
            with patch.dict(os.environ, {"PS_SEZHAO_PROJECT_DB": str(database)}):
                root = create_root()
                root.withdraw()
                app = create_application(root, initial_files=[str(image_path)])
                root.update_idletasks()
                app._save_project_session_now()
                self.assertEqual(len(ProjectStore(database).load_workspace().file_paths), 1)
                with patch(
                    "ps_sezhao.services.startup_close_policy.messagebox.askyesnocancel",
                    return_value=False,
                ):
                    app._close_with_project_prompt()
                self.assertEqual(ProjectStore(database).load_workspace().file_paths, ())
                self.assertIsNone(RollProjectStore(database).get_active_project_id())

    def test_close_save_creates_named_roll_and_clears_transient_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root_path = Path(directory)
            database = root_path / "workspace.sqlite3"
            image_path = self._create_image(root_path)
            with patch.dict(os.environ, {"PS_SEZHAO_PROJECT_DB": str(database)}):
                root = create_root()
                root.withdraw()
                app = create_application(root, initial_files=[str(image_path)])
                root.update_idletasks()
                with (
                    patch(
                        "ps_sezhao.services.startup_close_policy.messagebox.askyesnocancel",
                        return_value=True,
                    ),
                    patch(
                        "ps_sezhao.services.startup_close_policy.simpledialog.askstring",
                        return_value="测试胶卷",
                    ),
                ):
                    app._close_with_project_prompt()

                projects = RollProjectStore(database).list_projects()
                saved = next(project for project in projects if project.name == "测试胶卷")
                self.assertEqual(saved.item_count, 1)
                self.assertEqual(ProjectStore(database).load_workspace().file_paths, ())
                self.assertIsNone(RollProjectStore(database).get_active_project_id())


if __name__ == "__main__":
    unittest.main()

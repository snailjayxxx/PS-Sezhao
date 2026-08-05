from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ps_sezhao.storage import paths
from ps_sezhao.ui import create_application, create_root


class StyleStatusAndMacPathsV073Tests(unittest.TestCase):
    def test_style_popup_uses_right_pane_width_and_status_uses_top_panel(self) -> None:
        root = create_root()
        root.geometry("1500x900")
        try:
            app = create_application(root)
            root.update_idletasks()
            self.assertTrue(app._v073_style_status_applied)
            self.assertTrue(app._v073_top_status_panel.winfo_exists())

            app._v073_open_style_popup(app.film_profile_box)
            root.update_idletasks()
            popup = app._v073_style_popup
            self.assertIsNotNone(popup)
            self.assertGreaterEqual(
                popup.winfo_width(),
                app.style_library_frame.winfo_width() - 8,
            )
            self.assertGreaterEqual(popup.winfo_rootx(), app.style_library_frame.winfo_rootx())
            self.assertLessEqual(
                popup.winfo_rootx() + popup.winfo_width(),
                root.winfo_rootx() + root.winfo_width() + 2,
            )

            self.assertEqual(app._v072_crop_status_label.winfo_manager(), "")
            self.assertEqual(app._v072_geometry_status_label.winfo_manager(), "")
            app._v073_close_style_popup()
        finally:
            root.destroy()

    def test_installed_macos_app_creates_project_lut_and_logs_but_keeps_database_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_root = Path(temporary_directory) / "Library" / "Application Support" / "PS-Sezhao"
            with (
                patch.dict(os.environ, {}, clear=False),
                patch.object(paths.sys, "platform", "darwin"),
                patch.object(paths.sys, "frozen", True, create=True),
                patch.object(paths, "application_container", return_value=Path("/Applications")),
                patch.object(paths, "_legacy_data_root", return_value=data_root),
            ):
                os.environ.pop(paths.ENV_DATA_ROOT, None)
                os.environ.pop(paths.ENV_PROJECT_DATABASE, None)
                database = paths.default_project_database_path()
                project_directory = paths.default_project_directory()
                lut_directory = paths.default_lut_directory()
                log_directory = paths.default_log_directory()

            self.assertEqual(database, data_root / "workspace.sqlite3")
            self.assertEqual(project_directory, data_root / "project")
            self.assertEqual(lut_directory, data_root / "lut")
            self.assertEqual(log_directory, data_root / "logs")
            self.assertTrue(project_directory.is_dir())
            self.assertTrue(lut_directory.is_dir())
            self.assertTrue(log_directory.is_dir())
            self.assertTrue((project_directory / "README.txt").is_file())
            self.assertTrue((lut_directory / "README.txt").is_file())


if __name__ == "__main__":
    unittest.main()

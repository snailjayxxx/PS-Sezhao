from __future__ import annotations

import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from ps_sezhao.storage import paths
from ps_sezhao.ui import create_application, create_root


class StyleStatusAndMacPathsV073Tests(unittest.TestCase):
    def test_style_list_is_embedded_beside_label_and_status_uses_top_panel(self) -> None:
        root = create_root()
        root.geometry("1500x900")
        try:
            app = create_application(root)
            root.update_idletasks()
            self.assertTrue(app._v073_style_status_applied)
            self.assertTrue(app._v073_top_status_panel.winfo_exists())

            scanner = app._v073_inline_style_lists["scanner"]
            film = app._v073_inline_style_lists["film"]
            self.assertIs(scanner["block"].master, app.style_library_frame)
            self.assertIs(film["block"].master, app.style_library_frame)
            self.assertGreaterEqual(
                film["entry"].winfo_width(),
                app.style_library_frame.winfo_width() - 145,
            )

            top_levels_before = [
                widget for widget in root.winfo_children() if isinstance(widget, tk.Toplevel)
            ]
            app._v073_toggle_inline_style_list("film")
            root.update_idletasks()
            self.assertEqual(film["options"].winfo_manager(), "grid")
            self.assertGreater(film["listbox"].size(), 5)
            self.assertGreaterEqual(
                film["options"].winfo_width(),
                film["entry"].winfo_width() - 6,
            )
            top_levels_after = [
                widget for widget in root.winfo_children() if isinstance(widget, tk.Toplevel)
            ]
            self.assertEqual(top_levels_after, top_levels_before)

            film["listbox"].selection_clear(0, "end")
            film["listbox"].selection_set(1)
            selected = str(film["listbox"].get(1))
            app._v073_choose_inline_style("film")
            root.update_idletasks()
            self.assertEqual(app.film_profile_box.get(), selected)
            self.assertEqual(film["options"].winfo_manager(), "")

            self.assertEqual(app._v072_crop_status_label.winfo_manager(), "")
            self.assertEqual(app._v072_geometry_status_label.winfo_manager(), "")
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

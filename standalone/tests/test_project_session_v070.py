from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from ps_sezhao.ui import create_application, create_root


class ProjectSessionV070Tests(unittest.TestCase):
    def test_window_restores_last_files_parameters_crop_and_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root_path = Path(temporary_directory)
            database = root_path / "workspace.sqlite3"
            image_path = root_path / "negative.png"
            image = Image.new("RGB", (96, 72), (230, 145, 75))
            ImageDraw.Draw(image).rectangle((12, 10, 84, 62), fill=(80, 55, 40))
            image.save(image_path)

            with patch.dict(os.environ, {"PS_SEZHAO_PROJECT_DB": str(database)}):
                first_root = create_root()
                first_root.withdraw()
                try:
                    first_app = create_application(first_root, initial_files=[str(image_path)])
                    first_root.update_idletasks()
                    first_app.vars["exposure"].set(0.75)
                    first_app.crop_norm = (0.1, 0.2, 0.85, 0.9)
                    first_app.current_item().rotation = 90
                    first_app._store_current_state()
                    first_app._save_project_session_now()
                finally:
                    first_root.destroy()

                second_root = create_root()
                second_root.withdraw()
                try:
                    second_app = create_application(second_root)
                    second_root.update_idletasks()
                    self.assertEqual(len(second_app.items), 1)
                    self.assertEqual(second_app.items[0].path.resolve(), image_path.resolve())
                    self.assertAlmostEqual(second_app.vars["exposure"].get(), 0.75)
                    self.assertEqual(tuple(second_app.crop_norm), (0.1, 0.2, 0.85, 0.9))
                    self.assertEqual(second_app.current_item().rotation, 90)
                    self.assertIn("已恢复上次工作状态", second_app.status.get())
                finally:
                    second_root.destroy()


if __name__ == "__main__":
    unittest.main()

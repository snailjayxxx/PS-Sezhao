from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tkinter import ttk

from ps_sezhao.storage.paths import ENV_DATA_ROOT
from ps_sezhao.ui import create_application, create_root


IDENTITY_CUBE = """TITLE \"UI Identity\"
LUT_3D_SIZE 2
0 0 0
1 0 0
0 1 0
1 1 0
0 0 1
1 0 1
0 1 1
1 1 1
"""


class UiLayoutV072Tests(unittest.TestCase):
    def test_style_selectors_and_framed_tools_keep_fixed_internal_spacing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory, patch.dict(
            os.environ,
            {ENV_DATA_ROOT: temporary_directory},
            clear=False,
        ):
            lut_directory = Path(temporary_directory) / "lut"
            lut_directory.mkdir(parents=True)
            (lut_directory / "ui-test.cube").write_text(IDENTITY_CUBE, encoding="utf-8")

            root = create_root()
            root.geometry("1600x900")
            root.withdraw()
            try:
                application = create_application(root)
                root.update_idletasks()

                self.assertTrue(application._v072_workspace_lut_layout_applied)
                self.assertTrue(application._v072_responsive_group_applied)
                self.assertEqual(str(application.style_library_frame.cget("text")), "扫描仪与胶卷风格")
                self.assertIsNotNone(application.scanner_profile_box)
                self.assertIsNotNone(application.film_profile_box)
                assert application.scanner_profile_box is not None
                assert application.film_profile_box is not None
                self.assertEqual(int(application.scanner_profile_box.cget("width")), 1)
                self.assertEqual(int(application.film_profile_box.cget("width")), 1)
                film_values = tuple(str(value) for value in application.film_profile_box.cget("values"))
                self.assertIn("用户 LUT · ui-test", film_values)

                tool_groups = application._v072_tool_groups
                self.assertEqual(len(tool_groups), 3)
                self.assertTrue(all(isinstance(group, ttk.LabelFrame) for group in tool_groups))
                self.assertEqual(tuple(str(group.cget("text")) for group in tool_groups), ("裁切工具", "缩放", "旋转"))
                self.assertEqual(int(application._v072_viewbar.columnconfigure(4)["weight"]), 1)

                geometry_groups = application._v072_geometry_groups
                self.assertEqual(tuple(str(group.cget("text")) for group in geometry_groups), ("范围", "拉直", "变换"))
                self.assertEqual(int(application._v072_geometry_bar.columnconfigure(4)["weight"]), 1)

                application._layout_v072_preview_groups(SimpleNamespace(width=700))
                self.assertEqual(int(tool_groups[0].grid_info()["row"]), 0)
                self.assertEqual(int(tool_groups[1].grid_info()["row"]), 0)
                self.assertEqual(int(tool_groups[2].grid_info()["row"]), 1)
                self.assertEqual(int(tool_groups[2].grid_info()["column"]), 0)
                application._layout_v072_preview_groups(SimpleNamespace(width=1200))
                self.assertEqual(
                    tuple(int(group.grid_info()["column"]) for group in tool_groups),
                    (0, 1, 2),
                )
                self.assertEqual(int(tool_groups[2].grid_info()["row"]), 0)

                application._layout_v072_geometry_groups(SimpleNamespace(width=700))
                self.assertEqual(int(geometry_groups[0].grid_info()["row"]), 0)
                self.assertEqual(int(geometry_groups[1].grid_info()["row"]), 0)
                self.assertEqual(int(geometry_groups[2].grid_info()["row"]), 1)
                self.assertEqual(int(geometry_groups[2].grid_info()["column"]), 0)
                application._layout_v072_geometry_groups(SimpleNamespace(width=1200))
                self.assertEqual(
                    tuple(int(group.grid_info()["column"]) for group in geometry_groups),
                    (0, 1, 2),
                )
                self.assertEqual(int(geometry_groups[2].grid_info()["row"]), 0)

                self.assertTrue(application.project_folder_button.winfo_exists())
                self.assertTrue((Path(temporary_directory) / "project").is_dir())
                self.assertTrue((Path(temporary_directory) / "lut").is_dir())
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()

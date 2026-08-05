from __future__ import annotations

import unittest

from tkinter import ttk

from ps_sezhao.ui import create_application, create_root


class TextLayoutV071Tests(unittest.TestCase):
    def test_cjk_text_layout_keeps_global_and_roll_controls_compact(self) -> None:
        root = create_root()
        root.geometry("1280x800")
        root.withdraw()
        try:
            application = create_application(root)
            root.update_idletasks()

            self.assertTrue(application._v071_text_layout_applied)
            self.assertIsInstance(application._ps_sezhao_ui_font_family, str)

            self.assertEqual(int(application.roll_new_button.grid_info()["row"]), 2)
            self.assertEqual(int(application.roll_open_button.grid_info()["row"]), 2)
            self.assertEqual(int(application.roll_settings_button.grid_info()["row"]), 3)
            self.assertEqual(int(application.output_presets_button.grid_info()["row"]), 3)
            self.assertEqual(int(application.roll_new_button.grid_info()["column"]), 0)
            self.assertEqual(int(application.roll_open_button.grid_info()["column"]), 1)

            toolbar = next(
                child
                for child in root.winfo_children()
                if isinstance(child, ttk.Frame)
                and str(child.grid_info().get("row")) == "0"
            )
            toolbar_rows = {
                str(widget.cget("text")): int(widget.grid_info()["row"])
                for widget in toolbar.winfo_children()
                if isinstance(widget, ttk.Button) and widget.grid_info()
            }
            self.assertEqual(toolbar_rows["吸管：胶片基底"], 1)
            self.assertEqual(toolbar_rows["吸管：中性色"], 1)
            self.assertEqual(toolbar_rows["恢复默认"], 1)

            # Beta 3 replaces the old direct preview/geometry buttons with
            # framed groups after the v0.7.1 compatibility pass. The old bars
            # must remain valid containers and must not be destroyed.
            self.assertTrue(application._compact_preview_toolbar.winfo_exists())
            self.assertTrue(application._compact_geometry_toolbar.winfo_exists())
            self.assertTrue(application._v072_viewbar.winfo_exists())
            self.assertTrue(application._v072_geometry_bar.winfo_exists())
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

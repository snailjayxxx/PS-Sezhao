from __future__ import annotations

import unittest

from tkinter import ttk

from ps_sezhao.ui import create_application, create_root


class TextLayoutV071Tests(unittest.TestCase):
    def test_cjk_text_layout_uses_compact_rows_without_cross_pane_widgets(self) -> None:
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

            preview_bar = application._compact_preview_toolbar
            preview_rows = {
                str(widget.cget("text")): int(widget.grid_info()["row"])
                for widget in preview_bar.winfo_children()
                if isinstance(widget, ttk.Button) and widget.grid_info()
            }
            self.assertEqual(preview_rows["左转 90°"], 1)
            self.assertEqual(preview_rows["右转 90°"], 1)

            geometry_bar = application._compact_geometry_toolbar
            geometry_rows = {
                str(widget.cget("text")): int(widget.grid_info()["row"])
                for widget in geometry_bar.winfo_children()
                if isinstance(widget, ttk.Button) and widget.grid_info()
            }
            self.assertEqual(geometry_rows["水平翻转"], 1)
            self.assertEqual(geometry_rows["垂直翻转"], 1)
            self.assertEqual(geometry_rows["四角透视"], 1)
            self.assertEqual(geometry_rows["重置几何"], 1)

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
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

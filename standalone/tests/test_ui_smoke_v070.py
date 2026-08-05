from __future__ import annotations

import unittest

from ps_sezhao.ui import create_application, create_root


class StandaloneUiSmokeV070Tests(unittest.TestCase):
    def test_configured_window_builds_and_keeps_core_widgets_alive(self) -> None:
        root = create_root()
        root.withdraw()
        try:
            application = create_application(root)
            root.update_idletasks()

            self.assertTrue(root.winfo_exists())
            self.assertTrue(application.file_tree.winfo_exists())
            self.assertTrue(application.canvas.winfo_exists())
            self.assertTrue(application.controls.winfo_exists())
            self.assertTrue(application.main_panedwindow.winfo_exists())
            self.assertEqual(len(application.main_panedwindow.panes()), 3)

            raw_entries = getattr(application, "raw_custom_wb_entries", None)
            if raw_entries is not None:
                for entry in raw_entries:
                    self.assertTrue(entry.winfo_exists())
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

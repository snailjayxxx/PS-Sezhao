from __future__ import annotations

import tkinter as real_tk
import unittest

from ps_sezhao.app_v055_import_drop_patch import TkinterDnD, install_drag_drop_root


class DragDropRootTests(unittest.TestCase):
    def test_install_does_not_replace_global_tk_class(self) -> None:
        if TkinterDnD is None:
            self.skipTest("tkinterdnd2 is unavailable")

        original_tk_class = real_tk.Tk

        class FakeAppModule:
            tk = real_tk

        self.assertTrue(install_drag_drop_root(FakeAppModule))
        self.assertIs(real_tk.Tk, original_tk_class)
        self.assertIs(FakeAppModule.tk.Tk, TkinterDnD.Tk)
        self.assertIs(FakeAppModule.tk.Canvas, real_tk.Canvas)

        # Installing twice must remain safe and must not create nested proxies.
        self.assertTrue(install_drag_drop_root(FakeAppModule))
        self.assertIs(real_tk.Tk, original_tk_class)
        self.assertIs(FakeAppModule.tk.Tk, TkinterDnD.Tk)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tkinter as real_tk
import unittest
from unittest.mock import patch

from ps_sezhao.app_v055_import_drop_patch import (
    TkinterDnD,
    _SafeTkFactory,
    install_drag_drop_root,
)


class FakeRoot:
    pass


class DragDropRootTests(unittest.TestCase):
    def test_install_does_not_replace_global_tk_class(self) -> None:
        original_tk_class = real_tk.Tk

        class FakeAppModule:
            tk = real_tk

        installed = install_drag_drop_root(FakeAppModule)
        self.assertEqual(installed, TkinterDnD is not None)
        self.assertIs(real_tk.Tk, original_tk_class)
        self.assertIs(FakeAppModule.tk.Canvas, real_tk.Canvas)
        self.assertTrue(getattr(FakeAppModule.tk.Tk, "_ps_sezhao_safe_tk_factory", False))

        first_factory = FakeAppModule.tk.Tk
        self.assertEqual(install_drag_drop_root(FakeAppModule), TkinterDnD is not None)
        self.assertIs(FakeAppModule.tk.Tk, first_factory)
        self.assertIs(real_tk.Tk, original_tk_class)

    def test_incompatible_tkdnd_falls_back_to_normal_root(self) -> None:
        class FailingDnD:
            @staticmethod
            def require(_root: object) -> None:
                raise RuntimeError("interpreter uses an incompatible stubs mechanism")

        with patch("ps_sezhao.app_v055_import_drop_patch.TkinterDnD", FailingDnD):
            root = _SafeTkFactory(FakeRoot)()

        self.assertIsInstance(root, FakeRoot)
        self.assertFalse(root._ps_sezhao_dnd_available)
        self.assertIn("incompatible stubs mechanism", root._ps_sezhao_dnd_error)

    def test_successful_tkdnd_load_marks_capability(self) -> None:
        class WorkingDnD:
            @staticmethod
            def require(root: object) -> None:
                root.drop_target_register = lambda *_args: None
                root.dnd_bind = lambda *_args: None

        with patch("ps_sezhao.app_v055_import_drop_patch.TkinterDnD", WorkingDnD):
            root = _SafeTkFactory(FakeRoot)()

        self.assertTrue(root._ps_sezhao_dnd_available)
        self.assertIsNone(root._ps_sezhao_dnd_error)


if __name__ == "__main__":
    unittest.main()

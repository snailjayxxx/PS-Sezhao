from __future__ import annotations

import tkinter as real_tk
import unittest
from unittest.mock import patch

from ps_sezhao.app_v055_import_drop_patch import (
    TkinterDnD,
    build_safe_root_class,
    install_drag_drop_root,
)


class FakeRoot:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.tk = object()


class DragDropRootTests(unittest.TestCase):
    def test_install_does_not_replace_global_tk_class(self) -> None:
        original_tk_class = real_tk.Tk

        class FakeAppModule:
            tk = real_tk

        installed = install_drag_drop_root(FakeAppModule)
        self.assertEqual(installed, TkinterDnD is not None)
        self.assertIs(real_tk.Tk, original_tk_class)
        self.assertIs(FakeAppModule.tk.Canvas, real_tk.Canvas)
        self.assertTrue(
            getattr(FakeAppModule.tk.Tk, "_ps_sezhao_safe_tk_class", False)
        )

        first_class = FakeAppModule.tk.Tk
        self.assertEqual(install_drag_drop_root(FakeAppModule), TkinterDnD is not None)
        self.assertIs(FakeAppModule.tk.Tk, first_class)
        self.assertIs(real_tk.Tk, original_tk_class)

    def test_incompatible_tkdnd_falls_back_to_normal_root(self) -> None:
        class Wrapper:
            def drop_target_register(self, *_args: object) -> None:
                return None

            def dnd_bind(self, *_args: object) -> None:
                return None

        class FailingDnD:
            DnDWrapper = Wrapper

            @staticmethod
            def require(_root: object) -> None:
                raise RuntimeError("interpreter uses an incompatible stubs mechanism")

        with patch("ps_sezhao.app_v055_import_drop_patch.TkinterDnD", FailingDnD):
            safe_class = build_safe_root_class(FakeRoot)
            root = safe_class()

        self.assertIsInstance(root, FakeRoot)
        self.assertTrue(hasattr(root, "drop_target_register"))
        self.assertFalse(root._ps_sezhao_dnd_available)
        self.assertIn("incompatible stubs mechanism", root._ps_sezhao_dnd_error)

    def test_successful_tkdnd_load_keeps_wrapper_methods(self) -> None:
        class Wrapper:
            def drop_target_register(self, *_args: object) -> str:
                return "registered"

            def dnd_bind(self, *_args: object) -> str:
                return "bound"

        class WorkingDnD:
            DnDWrapper = Wrapper

            @staticmethod
            def require(_root: object) -> str:
                return "2.9.5"

        with patch("ps_sezhao.app_v055_import_drop_patch.TkinterDnD", WorkingDnD):
            safe_class = build_safe_root_class(FakeRoot)
            root = safe_class()

        self.assertTrue(root._ps_sezhao_dnd_available)
        self.assertEqual(root._ps_sezhao_dnd_version, "2.9.5")
        self.assertEqual(root.drop_target_register("DND_Files"), "registered")
        self.assertEqual(root.dnd_bind("<<Drop>>", object()), "bound")


if __name__ == "__main__":
    unittest.main()

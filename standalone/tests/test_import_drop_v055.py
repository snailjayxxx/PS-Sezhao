from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from ps_sezhao.app_v055_import_drop_patch import (
    SUPPORTED_SUFFIXES,
    apply_v055_import_drop_patch,
    install_drag_drop_root,
)


class FakeApp:
    def _build_ui(self) -> None:
        pass

    def open_paths(self, _paths, *, replace: bool = False) -> None:
        self.last_replace = replace

    def _detected_base(self):
        return "detected"

    def _direct_base_units(self):
        return "direct"

    def _set_direct_base_units(self, _values):
        return None

    def _item_key(self, _index=None):
        return "item"

    def _item_snapshot(self, _index=None):
        return {"ok": True}

    def _history_for(self, _index=None):
        return "history"

    def _record_history(self, **_kwargs):
        return None

    def _restore_snapshot(self, _snapshot):
        return None

    def _update_history_buttons(self):
        return None


class ImportDropV055Tests(unittest.TestCase):
    def setUp(self) -> None:
        apply_v055_import_drop_patch(FakeApp)

    def test_v054_public_aliases_are_repaired(self) -> None:
        self.assertIs(FakeApp.history_for, FakeApp._history_for)
        self.assertIs(FakeApp.detected_base, FakeApp._detected_base)
        self.assertIs(FakeApp.direct_base_units, FakeApp._direct_base_units)
        self.assertIs(FakeApp.record_history, FakeApp._record_history)

    def test_drop_parser_preserves_paths_with_spaces(self) -> None:
        app = object.__new__(FakeApp)
        app.root = SimpleNamespace(
            tk=SimpleNamespace(splitlist=lambda _raw: ("C:/Film Roll/frame 01.tif", "C:/RAW/shot.cr3"))
        )
        paths = app._parse_drop_paths("ignored")
        self.assertEqual(paths[0], Path("C:/Film Roll/frame 01.tif"))
        self.assertEqual(paths[1].suffix.lower(), ".cr3")

    def test_dropped_folder_discovers_images_and_raw_recursively(self) -> None:
        app = object.__new__(FakeApp)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            (root / "scan.tif").write_bytes(b"tif")
            (nested / "camera.nef").write_bytes(b"raw")
            (nested / "notes.txt").write_text("ignore", encoding="utf-8")
            found = app._discover_dropped_folder(root)
        self.assertEqual({path.suffix.lower() for path in found}, {".tif", ".nef"})

    def test_supported_suffixes_include_regular_and_raw_files(self) -> None:
        for extension in (".tif", ".jpg", ".dng", ".cr3", ".nef", ".nrw", ".arw", ".raf"):
            self.assertIn(extension, SUPPORTED_SUFFIXES)

    def test_drag_drop_root_installer_is_safe(self) -> None:
        fake_module = SimpleNamespace(tk=SimpleNamespace(Tk=object))
        result = install_drag_drop_root(fake_module)
        self.assertIsInstance(result, bool)
        if result:
            self.assertNotEqual(fake_module.tk.Tk, object)


if __name__ == "__main__":
    unittest.main()

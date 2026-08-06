from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ps_sezhao import app_v055_import_drop_patch as import_drop_patch
from ps_sezhao.app_v055_import_drop_patch import (
    apply_v055_import_drop_patch,
    collect_supported_paths,
    install_drag_drop_root,
    tkdnd_supported_on_platform,
)


class ImportDropPatchTests(unittest.TestCase):
    def test_collect_supported_paths_expands_folders_and_raw(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nested = root / "nested"
            nested.mkdir()
            jpg = root / "frame.JPG"
            raw = nested / "scan.NEF"
            ignored = nested / "notes.txt"
            jpg.write_bytes(b"jpg")
            raw.write_bytes(b"raw")
            ignored.write_text("ignore", encoding="utf-8")

            found = collect_supported_paths([root, jpg])
            self.assertEqual({_resolved(path) for path in found}, {_resolved(jpg), _resolved(raw)})

    def test_v054_internal_methods_are_republished_for_import(self) -> None:
        class FakeApp:
            def _build_ui(self) -> None:
                return None

        method_names = (
            "detected_base",
            "direct_base_units",
            "set_direct_base_units",
            "item_key",
            "item_snapshot",
            "history_for",
            "record_history",
            "restore_snapshot",
            "update_history_buttons",
        )
        for name in method_names:
            setattr(FakeApp, f"_{name}", lambda self, marker=name: marker)

        apply_v055_import_drop_patch(FakeApp)

        instance = FakeApp()
        for name in method_names:
            self.assertTrue(hasattr(FakeApp, name), name)
            self.assertEqual(getattr(instance, name)(), name)

    def test_macos_never_loads_or_installs_native_tkdnd(self) -> None:
        self.assertFalse(tkdnd_supported_on_platform("darwin"))
        self.assertTrue(tkdnd_supported_on_platform("win32"))
        self.assertTrue(tkdnd_supported_on_platform("linux"))

        class FakeTkModule:
            class Tk:
                pass

        class FakeAppModule:
            tk = FakeTkModule

        original_tk = FakeAppModule.tk
        with patch.object(import_drop_patch.sys, "platform", "darwin"):
            installed = install_drag_drop_root(FakeAppModule)
            available, error, version = import_drop_patch._load_tkdnd(object())

        self.assertFalse(installed)
        self.assertIs(FakeAppModule.tk, original_tk)
        self.assertFalse(available)
        self.assertIn("macOS", error or "")
        self.assertIsNone(version)

    def test_release_configuration_contains_safe_drag_drop_runtime(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        version = (project_root / "VERSION").read_text(encoding="utf-8").strip()
        core_version = version.split("-", 1)[0]
        package = json.loads((project_root / "package.json").read_text(encoding="utf-8"))
        manifest = json.loads((project_root / "plugin/manifest.json").read_text(encoding="utf-8"))
        runtime_entry = (project_root / "plugin/runtime-v022.js").read_text(encoding="utf-8")
        runtime_final = (project_root / "plugin/runtime-final.js").read_text(encoding="utf-8")
        lightroom_info = (project_root / "lightroom-classic/PS-Sezhao.lrplugin/Info.lua").read_text(encoding="utf-8")
        bootstrap = (project_root / "standalone/ps_sezhao/bootstrap.py").read_text(encoding="utf-8")
        groups = (project_root / "standalone/ps_sezhao/integration_groups.py").read_text(encoding="utf-8")
        requirements = (project_root / "standalone/requirements.txt").read_text(encoding="utf-8")
        workflow = (project_root / ".github/workflows/release.yml").read_text(encoding="utf-8")
        hook = (project_root / "hook-tkinterdnd2.py").read_text(encoding="utf-8")
        import_patch = (project_root / "standalone/ps_sezhao/app_v055_import_drop_patch.py").read_text(encoding="utf-8")

        self.assertEqual(package["version"], version)
        self.assertEqual(manifest["version"], core_version)
        self.assertIn(f'const VERSION = "{version}"', runtime_entry)
        self.assertIn(f'const VERSION = "{version}"', runtime_final)
        major, minor, revision = core_version.split(".")
        self.assertIn(
            f"major = {major}, minor = {minor}, revision = {revision}",
            lightroom_info,
        )
        self.assertIn("apply_v055_import_drop_patch", groups)
        self.assertIn("install_drag_drop_root", groups)
        self.assertIn("requested_gui_smoke", bootstrap)
        self.assertIn("tkinterdnd2>=0.6.2,<0.7", requirements)
        self.assertEqual(workflow.count("--collect-all tkinterdnd2"), 1)
        self.assertIn("--gui-smoke-test", workflow)
        self.assertIn("--require-dnd", workflow)
        self.assertIn("--exclude-module tkinterdnd2", workflow)
        self.assertIn("dnd=disabled", workflow)
        self.assertIn("MACOS_DND_DISABLED_REASON", import_patch)
        self.assertIn("tkdnd_supported_on_platform", import_patch)
        self.assertIn("collect_data_files", hook)


def _resolved(path: Path) -> str:
    return str(path.resolve(strict=False)).casefold()


if __name__ == "__main__":
    unittest.main()

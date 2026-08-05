from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ps_sezhao.bootstrap import configure_application, integration_steps
from ps_sezhao.core.contracts import (
    GEOMETRY_CONTRACT_VERSION,
    MATH_CONTRACT_VERSION,
    OUTPUT_QUEUE_CONTRACT_VERSION,
    PROJECT_SCHEMA_VERSION,
    PROXY_CONTRACT_VERSION,
    RAW_DECODE_CONTRACT_VERSION,
)
from ps_sezhao.services.import_service import collect_supported_paths
from ps_sezhao.storage import ProjectStore


class ArchitectureV070Tests(unittest.TestCase):
    def test_bootstrap_order_is_explicit_unique_and_idempotent(self) -> None:
        names = tuple(step.name for step in integration_steps())
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names[:3], ("engine.base", "engine.styles", "runtime.bindings"))
        for required in (
            "services.preview_proxy",
            "services.geometry",
            "services.geometry_history",
            "services.output_queue",
            "services.module_sync",
            "services.lightroom_jobs",
            "storage.project_session",
        ):
            self.assertIn(required, names)
        self.assertLess(names.index("services.preview_proxy"), names.index("services.geometry"))
        self.assertLess(names.index("services.geometry"), names.index("services.output_queue"))
        self.assertLess(names.index("services.output_queue"), names.index("services.module_sync"))
        self.assertLess(names.index("services.module_sync"), names.index("services.lightroom_jobs"))
        self.assertLess(names.index("services.lightroom_jobs"), names.index("storage.project_session"))
        self.assertEqual(names[-1], "runtime.drag_drop_root")

        first = configure_application()
        second = configure_application()
        self.assertEqual(first.steps, names)
        self.assertEqual(second.steps, names)
        self.assertFalse(second.configured_now)

    def test_main_only_calls_the_unified_entrypoint(self) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "standalone/main.py").read_text(encoding="utf-8")
        self.assertIn("run_application", source)
        self.assertNotIn("app_v0", source)
        self.assertNotIn("apply_patch", source)
        self.assertNotIn("apply_raw_patch", source)

    def test_import_service_recursively_expands_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nested = root / "nested"
            nested.mkdir()
            first = root / "one.ARW"
            second = nested / "two.tif"
            ignored = nested / "notes.txt"
            first.write_bytes(b"raw")
            second.write_bytes(b"tiff")
            ignored.write_text("ignore", encoding="utf-8")

            found = collect_supported_paths([root, first])
            self.assertEqual(
                {path.resolve() for path in found},
                {first.resolve(), second.resolve()},
            )

    def test_project_store_round_trip_records_contract_versions_and_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "project.sqlite3"
            first = root / "scan.ARW"
            second = root / "scan2.tif"
            store = ProjectStore(database)
            store.save_session(
                image_states=[
                    {
                        "file_path": first,
                        "controls": {"exposure": 0.25, "profile": "generic"},
                        "analysis": {"base": [0.9, 0.6, 0.4]},
                        "crop": (0.1, 0.2, 0.8, 0.9),
                        "rotation": 450,
                        "geometry": {"straighten": 1.2},
                        "raw_settings": {"wb_mode": "daylight"},
                        "output_settings": {"format_label": "JPEG", "jpeg_quality": 90},
                    }
                ],
                file_paths=[first, second],
                current_file=first,
                updated_at=123,
            )
            state = store.load_image_state(first)
            workspace = store.load_workspace()

            self.assertIsNotNone(state)
            assert state is not None
            self.assertEqual(state.rotation, 90)
            self.assertEqual(state.controls["exposure"], 0.25)
            self.assertEqual(state.crop, (0.1, 0.2, 0.8, 0.9))
            self.assertAlmostEqual(state.geometry["straighten"], 1.2)
            self.assertEqual(state.raw_settings["wb_mode"], "daylight")
            self.assertEqual(state.output_settings["jpeg_quality"], 90)
            self.assertEqual(state.math_version, MATH_CONTRACT_VERSION)
            self.assertEqual(state.raw_decode_version, RAW_DECODE_CONTRACT_VERSION)
            self.assertEqual(tuple(Path(path) for path in workspace.file_paths), (first, second))
            self.assertEqual(Path(workspace.current_file or ""), first)
            self.assertGreaterEqual(PROJECT_SCHEMA_VERSION, 3)
            self.assertGreaterEqual(PROXY_CONTRACT_VERSION, 1)
            self.assertGreaterEqual(OUTPUT_QUEUE_CONTRACT_VERSION, 1)
            self.assertGreaterEqual(GEOMETRY_CONTRACT_VERSION, 1)

    def test_architecture_document_uses_only_internal_optimization_language(self) -> None:
        root = Path(__file__).resolve().parents[2]
        document = (root / "docs/architecture-refactor-plan.md").read_text(encoding="utf-8")
        self.assertNotIn("NexFilm", document)
        self.assertNotIn("参考", document)


if __name__ == "__main__":
    unittest.main()

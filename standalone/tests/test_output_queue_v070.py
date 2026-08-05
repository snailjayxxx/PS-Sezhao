from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from ps_sezhao.engine import Analysis, Controls
from ps_sezhao.processing import ProcessingCancelled, process_image_tiled
from ps_sezhao.services import output_service
from ps_sezhao.services.output_service import (
    ExportTask,
    OutputQueueService,
    reserve_unique_destination,
)


def _analysis() -> Analysis:
    return Analysis(
        base=(0.92, 0.64, 0.38),
        black=(0.0, 0.0, 0.0),
        white=(1.25, 1.20, 1.15),
    )


def _task(source: Path, destination: Path) -> ExportTask:
    return ExportTask(
        source=source,
        destination=destination,
        controls=Controls(),
        crop=(0.0, 0.0, 1.0, 1.0),
        analysis=_analysis(),
        bit_depth=8,
        jpeg_quality=92,
    )


class OutputQueueV070Tests(unittest.TestCase):
    def test_processing_can_cancel_between_tiles(self) -> None:
        image = np.full((160, 12, 3), 0.4, dtype=np.float32)
        cancel = threading.Event()

        def progress(value: float) -> None:
            if value > 0:
                cancel.set()

        with self.assertRaises(ProcessingCancelled):
            process_image_tiled(
                image,
                _analysis(),
                Controls(),
                tile_rows=32,
                should_cancel=cancel.is_set,
                progress_callback=progress,
            )

    def test_batch_exports_in_background_and_reports_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "first.png"
            second = root / "second.png"
            Image.new("RGB", (48, 36), (140, 80, 40)).save(first)
            Image.new("RGB", (48, 36), (100, 70, 30)).save(second)
            tasks = [
                _task(first, root / "out-first.png"),
                _task(second, root / "out-second.png"),
            ]
            completed = threading.Event()
            summaries = []
            events = []
            service = OutputQueueService()
            try:
                service.submit(
                    tasks,
                    on_event=events.append,
                    on_complete=lambda summary: (summaries.append(summary), completed.set()),
                )
                self.assertTrue(completed.wait(timeout=10))
            finally:
                service.shutdown()

            self.assertEqual(len(summaries), 1)
            summary = summaries[0]
            self.assertEqual(summary.succeeded, 2)
            self.assertEqual(summary.failed, 0)
            self.assertEqual(summary.cancelled, 0)
            self.assertTrue((root / "out-first.png").is_file())
            self.assertTrue((root / "out-second.png").is_file())
            progress = [event.overall_progress for event in events if event.kind == "item_progress"]
            self.assertTrue(progress)
            self.assertGreater(max(progress), 0.5)

    def test_one_failure_does_not_stop_later_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            good = root / "good.png"
            Image.new("RGB", (40, 30), (120, 90, 60)).save(good)
            completed = threading.Event()
            summaries = []
            service = OutputQueueService()
            try:
                service.submit(
                    [
                        _task(root / "missing.png", root / "missing-out.png"),
                        _task(good, root / "good-out.png"),
                    ],
                    on_complete=lambda summary: (summaries.append(summary), completed.set()),
                )
                self.assertTrue(completed.wait(timeout=10))
            finally:
                service.shutdown()

            summary = summaries[0]
            self.assertEqual(summary.failed, 1)
            self.assertEqual(summary.succeeded, 1)
            self.assertEqual(len(summary.failures), 1)
            self.assertTrue((root / "good-out.png").is_file())

    def test_cancel_stops_current_batch_without_partial_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.png"
            Image.new("RGB", (32, 24), (100, 80, 50)).save(source)
            started = threading.Event()
            release = threading.Event()
            completed = threading.Event()
            summaries = []
            original_load = output_service.load_image

            def slow_load(*args: object, **kwargs: object):
                started.set()
                self.assertTrue(release.wait(timeout=5))
                return original_load(*args, **kwargs)

            service = OutputQueueService()
            try:
                with mock.patch.object(output_service, "load_image", side_effect=slow_load):
                    batch_id = service.submit(
                        [
                            _task(source, root / "one.png"),
                            _task(source, root / "two.png"),
                        ],
                        on_complete=lambda summary: (summaries.append(summary), completed.set()),
                    )
                    self.assertTrue(started.wait(timeout=5))
                    self.assertTrue(service.cancel(batch_id))
                    release.set()
                    self.assertTrue(completed.wait(timeout=10))
            finally:
                service.shutdown()

            summary = summaries[0]
            self.assertEqual(summary.succeeded, 0)
            self.assertEqual(summary.failed, 0)
            self.assertEqual(summary.cancelled, 2)
            self.assertFalse((root / "one.png").exists())
            self.assertFalse((root / "two.png").exists())

    def test_batch_destinations_avoid_existing_and_duplicate_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            existing = root / "scan_PS-Sezhao.tif"
            existing.write_bytes(b"existing")
            reserved: set[str] = set()
            first = reserve_unique_destination(existing, reserved)
            second = reserve_unique_destination(existing, reserved)

            self.assertEqual(first.name, "scan_PS-Sezhao_2.tif")
            self.assertEqual(second.name, "scan_PS-Sezhao_3.tif")
            self.assertEqual(existing.read_bytes(), b"existing")

    def test_ui_pipeline_is_wired_after_preview_proxy(self) -> None:
        root = Path(__file__).resolve().parents[2]
        bootstrap = (root / "standalone/ps_sezhao/bootstrap.py").read_text(encoding="utf-8")
        pipeline = (
            root / "standalone/ps_sezhao/services/output_pipeline.py"
        ).read_text(encoding="utf-8")
        document = (root / "docs/architecture-refactor-plan.md").read_text(encoding="utf-8")

        self.assertIn('IntegrationStep("services.output_queue"', bootstrap)
        self.assertLess(
            bootstrap.index('IntegrationStep("services.preview_proxy"'),
            bootstrap.index('IntegrationStep("services.output_queue"'),
        )
        for token in (
            "取消导出",
            "_submit_export_tasks",
            "reserve_unique_destination",
            "_handle_export_complete",
        ):
            self.assertIn(token, pipeline)
        self.assertNotIn("NexFilm", document)
        self.assertNotIn("参考", document)


if __name__ == "__main__":
    unittest.main()

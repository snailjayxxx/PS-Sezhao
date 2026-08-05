from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest

import numpy as np
from PIL import Image
import tifffile

from ps_sezhao.bootstrap import configure_application, integration_steps
from ps_sezhao.color_profiles import PROPHOTO_RGB_V2_MICRO
from ps_sezhao.core.output import (
    ContactSheetEntry,
    OutputSettings,
    apply_output_sharpening,
    build_contact_sheet,
    calculate_resize_dimensions,
    prepare_output,
    render_filename,
    resolve_destination,
    save_output_file,
)
from ps_sezhao.engine import Controls
from ps_sezhao.services.complete_output_pipeline import CompleteExportTask
from ps_sezhao.services.output_service import OutputQueueService


class OutputContractTests(unittest.TestCase):
    def test_settings_sanitize_format_resize_and_metadata(self) -> None:
        settings = OutputSettings(
            format_label="unknown",
            jpeg_quality=999,
            color_space="bad",
            resize_mode="bad",
            resize_value=float("nan"),
            filename_template="",
            contact_columns=99,
            contact_cell_size=20,
        ).sanitized()
        self.assertEqual(settings.format_label, "16 位 TIFF（无损）")
        self.assertEqual(settings.jpeg_quality, 100)
        self.assertEqual(settings.color_space, "prophoto")
        self.assertEqual(settings.resize_mode, "original")
        self.assertEqual(settings.filename_template, "{stem}_PS-Sezhao")
        self.assertEqual(settings.contact_columns, 12)
        self.assertEqual(settings.contact_cell_size, 120)

    def test_resize_modes_preserve_aspect_ratio_and_upscale_policy(self) -> None:
        self.assertEqual(
            calculate_resize_dimensions(
                4000,
                2000,
                OutputSettings(resize_mode="long_edge", resize_value=1000),
            ),
            (1000, 500),
        )
        self.assertEqual(
            calculate_resize_dimensions(
                400,
                200,
                OutputSettings(resize_mode="width", resize_value=800, allow_upscale=False),
            ),
            (400, 200),
        )
        self.assertEqual(
            calculate_resize_dimensions(
                400,
                200,
                OutputSettings(resize_mode="width", resize_value=800, allow_upscale=True),
            ),
            (800, 400),
        )

    def test_prepare_output_converts_prophoto_to_srgb_resizes_and_sharpens(self) -> None:
        image = np.zeros((40, 80, 3), dtype=np.float32)
        image[:, :40] = (0.8, 0.35, 0.15)
        image[:, 40:] = (0.2, 0.65, 0.75)
        settings = OutputSettings(
            color_space="srgb",
            resize_mode="long_edge",
            resize_value=32,
            sharpen="standard",
        )
        prepared = prepare_output(
            image,
            settings,
            source_icc_profile=PROPHOTO_RGB_V2_MICRO,
            source_metadata={"linear_raw": True, "path": "scan.ARW"},
        )
        self.assertEqual(prepared.image.shape[:2], (16, 32))
        self.assertIsNotNone(prepared.icc_profile)
        self.assertTrue(np.isfinite(prepared.image).all())
        self.assertFalse(np.allclose(prepared.image[:, :16].mean(axis=(0, 1)), image[:, :40].mean(axis=(0, 1))))
        self.assertEqual(prepared.metadata["SourceFile"], "scan.ARW")

    def test_sharpening_changes_edges_but_not_flat_images(self) -> None:
        flat = np.full((12, 12, 3), 0.5, dtype=np.float32)
        np.testing.assert_allclose(apply_output_sharpening(flat, "high"), flat)
        edge = flat.copy()
        edge[:, 6:] = 0.8
        sharpened = apply_output_sharpening(edge, "standard")
        self.assertGreater(float(np.abs(sharpened - edge).max()), 0.001)

    def test_filename_template_is_sanitized_and_collision_policy_is_deterministic(self) -> None:
        settings = OutputSettings(
            filename_template="{roll}:{film}/{frame}_{stem}",
            roll_name="Roll 01",
            film_stock="Portra 400",
            frame_number="A-03",
        )
        name = render_filename("scan:01.tif", settings, index=3, sequence=3)
        self.assertNotIn(":", name)
        self.assertNotIn("/", name)
        self.assertIn("Roll 01", name)
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "scan.jpg"
            first.write_bytes(b"existing")
            reserved: set[str] = set()
            second = resolve_destination(first, "auto_number", reserved)
            self.assertEqual(second.name, "scan_2.jpg")
            self.assertIsNone(resolve_destination(first, "skip", set()))
            with self.assertRaises(FileExistsError):
                resolve_destination(first, "error", set())

    def test_metadata_is_written_to_png_jpeg_and_tiff(self) -> None:
        image = np.full((12, 16, 3), (0.25, 0.5, 0.75), dtype=np.float32)
        metadata = {
            "FilmStock": "Portra 400",
            "Camera": "Hasselblad",
            "CaptureDate": "2026-08-05",
            "FrameNumber": "12",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            png = root / "metadata.png"
            jpg = root / "metadata.jpg"
            tif = root / "metadata.tif"
            save_output_file(png, image, bit_depth=8, icc_profile=None, jpeg_quality=90, metadata=metadata)
            save_output_file(jpg, image, bit_depth=8, icc_profile=None, jpeg_quality=90, metadata=metadata)
            save_output_file(tif, image, bit_depth=16, icc_profile=PROPHOTO_RGB_V2_MICRO, jpeg_quality=90, metadata=metadata)
            with Image.open(png) as loaded_png:
                self.assertEqual(loaded_png.info["FilmStock"], "Portra 400")
            with Image.open(jpg) as loaded_jpg:
                description = loaded_jpg.getexif().get(270, "")
                self.assertEqual(json.loads(description)["Camera"], "Hasselblad")
            with tifffile.TiffFile(tif) as loaded_tif:
                self.assertEqual(json.loads(loaded_tif.pages[0].description)["FrameNumber"], "12")
                self.assertEqual(loaded_tif.asarray().dtype, np.uint16)

    def test_contact_sheet_dimensions_follow_grid_settings(self) -> None:
        entries = [
            ContactSheetEntry(np.full((40, 60, 3), index / 10.0, dtype=np.float32), f"scan-{index}")
            for index in range(7)
        ]
        settings = OutputSettings(
            contact_columns=3,
            contact_cell_size=180,
            contact_labels=True,
            contact_background="light",
        )
        sheet = build_contact_sheet(entries, settings)
        self.assertEqual(sheet.shape[1], 3 * 180)
        self.assertEqual(sheet.shape[0], 3 * (180 + 28))
        self.assertEqual(sheet.dtype, np.float32)


class OutputQueueIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configure_application()

    def test_complete_export_task_runs_final_size_color_and_metadata_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "negative.png"
            target = root / "Roll01_0001.jpg"
            pixels = np.zeros((60, 120, 3), dtype=np.uint8)
            pixels[:, :] = (235, 145, 70)
            pixels[10:50, 20:100] = (80, 55, 35)
            Image.fromarray(pixels, mode="RGB").save(source)
            settings = OutputSettings(
                format_label="JPEG",
                color_space="srgb",
                resize_mode="long_edge",
                resize_value=48,
                sharpen="low",
                film_stock="Gold 200",
                frame_number="0001",
            )
            task = CompleteExportTask(
                source=source,
                destination=target,
                controls=Controls(),
                crop=(0.0, 0.0, 1.0, 1.0),
                output_settings=settings,
            )
            completed = threading.Event()
            summaries = []
            service = OutputQueueService()
            try:
                service.submit(
                    [task],
                    on_complete=lambda summary: (summaries.append(summary), completed.set()),
                )
                self.assertTrue(completed.wait(20.0))
            finally:
                service.shutdown()
            self.assertEqual(summaries[0].succeeded, 1)
            with Image.open(target) as exported:
                self.assertEqual(max(exported.size), 48)
                description = json.loads(exported.getexif().get(270, "{}"))
                self.assertEqual(description["FilmStock"], "Gold 200")

    def test_bootstrap_places_complete_output_between_queue_and_module_sync(self) -> None:
        names = tuple(step.name for step in integration_steps())
        self.assertLess(names.index("services.output_queue"), names.index("services.complete_output"))
        self.assertLess(names.index("services.complete_output"), names.index("services.module_sync"))
        self.assertLess(names.index("services.module_sync"), names.index("services.output_sync"))


if __name__ == "__main__":
    unittest.main()

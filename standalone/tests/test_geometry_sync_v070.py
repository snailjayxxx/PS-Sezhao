from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from ps_sezhao.core.geometry import (
    GeometrySettings,
    IDENTITY_PERSPECTIVE,
    apply_photo_geometry,
    detect_frame_bounds,
    perspective_is_identity,
    rotate_geometry,
)
from ps_sezhao.services.sync_pipeline import copy_modules
from ps_sezhao.storage.project_store import ProjectStore
from ps_sezhao.workspace import PhotoState


class GeometryCoreTests(unittest.TestCase):
    def test_identity_and_flips_keep_float_pipeline(self) -> None:
        image = np.arange(3 * 4 * 3, dtype=np.float32).reshape(3, 4, 3) / 36.0
        identity = apply_photo_geometry(image, GeometrySettings())
        np.testing.assert_allclose(identity, image)
        flipped = apply_photo_geometry(
            image,
            GeometrySettings(flip_horizontal=True, flip_vertical=True),
        )
        np.testing.assert_allclose(flipped, image[::-1, ::-1])
        self.assertEqual(flipped.dtype, np.float32)

    def test_straighten_and_perspective_are_available_in_one_geometry_contract(self) -> None:
        image = np.zeros((80, 120, 3), dtype=np.float32)
        image[15:65, 25:95] = (0.8, 0.4, 0.2)
        geometry = GeometrySettings(
            straighten=2.0,
            perspective=((0.12, 0.08), (0.88, 0.12), (0.92, 0.90), (0.08, 0.86)),
        )
        result = apply_photo_geometry(image, geometry)
        self.assertEqual(result.ndim, 3)
        self.assertGreater(result.shape[0], 20)
        self.assertGreater(result.shape[1], 20)
        self.assertTrue(np.isfinite(result).all())
        self.assertFalse(perspective_is_identity(geometry.perspective))

    def test_geometry_rotates_perspective_with_quarter_turn(self) -> None:
        geometry = GeometrySettings(
            flip_horizontal=True,
            perspective=((0.1, 0.2), (0.8, 0.1), (0.9, 0.8), (0.2, 0.9)),
        )
        rotated = rotate_geometry(geometry, 90)
        self.assertNotEqual(rotated.perspective, geometry.perspective)
        self.assertFalse(rotated.flip_horizontal)
        self.assertTrue(rotated.flip_vertical)

    def test_frame_detection_returns_confidence_and_safe_fallback(self) -> None:
        image = np.full((240, 360, 3), 0.05, dtype=np.float32)
        inner_y = np.linspace(0.2, 0.9, 170, dtype=np.float32)[:, None, None]
        inner_x = np.linspace(0.1, 0.8, 260, dtype=np.float32)[None, :, None]
        content = np.concatenate(
            [
                np.broadcast_to(inner_x, (170, 260, 1)),
                np.broadcast_to(inner_y, (170, 260, 1)),
                np.broadcast_to((inner_x + inner_y) / 2.0, (170, 260, 1)),
            ],
            axis=2,
        )
        image[35:205, 50:310] = content
        detection = detect_frame_bounds(image)
        self.assertFalse(detection.used_fallback)
        self.assertGreaterEqual(detection.confidence, 0.30)
        left, top, right, bottom = detection.crop
        self.assertAlmostEqual(left, 50 / 360, delta=0.06)
        self.assertAlmostEqual(top, 35 / 240, delta=0.06)
        self.assertAlmostEqual(right, 310 / 360, delta=0.06)
        self.assertAlmostEqual(bottom, 205 / 240, delta=0.06)

        uniform = detect_frame_bounds(np.full((100, 120, 3), 0.5, dtype=np.float32))
        self.assertTrue(uniform.used_fallback)
        self.assertEqual(uniform.crop, (0.0, 0.0, 1.0, 1.0))


class ModuleSyncTests(unittest.TestCase):
    def test_copy_modules_only_replaces_requested_sections(self) -> None:
        source = PhotoState(
            Path("source.tif"),
            controls={
                "profile": "kodak_portra_400",
                "style_strength": 0.8,
                "exposure": 1.2,
                "temperature": 0.3,
                "base_adjust": (0.1, 0.2, 0.3),
            },
            analysis={"base": [0.9, 0.6, 0.4], "black": [0, 0, 0], "white": [1, 1, 1]},
            crop=(0.1, 0.1, 0.9, 0.9),
            rotation=90,
            geometry=GeometrySettings(straighten=1.5, flip_horizontal=True).to_dict(),
            raw_settings={"wb_mode": "daylight"},
            output_settings={"format_label": "JPEG", "jpeg_quality": 91},
        )
        target = PhotoState(
            Path("target.tif"),
            controls={
                "profile": "generic",
                "style_strength": 1.0,
                "exposure": -0.5,
                "temperature": -0.2,
                "base_adjust": (0.0, 0.0, 0.0),
            },
            crop=(0.0, 0.0, 1.0, 1.0),
            rotation=0,
            geometry=GeometrySettings().to_dict(),
            raw_settings={"wb_mode": "camera"},
            output_settings={"format_label": "16 位 TIFF（无损）", "jpeg_quality": 95},
        )

        result = copy_modules(source, target, {"styles", "geometry", "crop"})
        self.assertEqual(result.controls["profile"], "kodak_portra_400")
        self.assertEqual(result.controls["style_strength"], 0.8)
        self.assertEqual(result.controls["exposure"], -0.5)
        self.assertEqual(result.controls["temperature"], -0.2)
        self.assertEqual(result.rotation, 90)
        self.assertEqual(result.crop, source.crop)
        self.assertEqual(result.raw_settings, target.raw_settings)
        self.assertEqual(result.output_settings, target.output_settings)

    def test_project_store_migrates_and_restores_new_per_photo_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "workspace.sqlite3"
            store = ProjectStore(database)
            store.save_image_state(
                file_path="scan.tif",
                controls={"exposure": 0.2},
                analysis=None,
                crop=(0.1, 0.2, 0.8, 0.9),
                rotation=270,
                geometry=GeometrySettings(straighten=-1.2).to_dict(),
                raw_settings={"wb_mode": "daylight"},
                output_settings={"format_label": "JPEG", "jpeg_quality": 88},
            )
            restored = store.load_image_state("scan.tif")
            assert restored is not None
            self.assertAlmostEqual(restored.geometry["straighten"], -1.2)
            self.assertEqual(restored.raw_settings["wb_mode"], "daylight")
            self.assertEqual(restored.output_settings["jpeg_quality"], 88)

    def test_default_perspective_is_stable(self) -> None:
        self.assertTrue(perspective_is_identity(IDENTITY_PERSPECTIVE))


if __name__ == "__main__":
    unittest.main()

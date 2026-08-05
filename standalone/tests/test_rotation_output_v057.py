from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from ps_sezhao.workspace import (
    PhotoState,
    normalize_rotation,
    rotate_array,
    rotate_crop,
)


class RotationAndOutputV057Tests(unittest.TestCase):
    def test_clockwise_rotation_uses_quarter_turns(self) -> None:
        source = np.array(
            [
                [[1], [2], [3]],
                [[4], [5], [6]],
            ],
            dtype=np.float32,
        )
        clockwise = rotate_array(source, 90)[..., 0]
        counter_clockwise = rotate_array(source, -90)[..., 0]

        np.testing.assert_array_equal(
            clockwise,
            np.array([[4, 1], [5, 2], [6, 3]], dtype=np.float32),
        )
        np.testing.assert_array_equal(
            counter_clockwise,
            np.array([[3, 6], [2, 5], [1, 4]], dtype=np.float32),
        )
        self.assertEqual(normalize_rotation(450), 90)
        self.assertEqual(normalize_rotation(-90), 270)

    def test_crop_rotates_with_same_physical_area(self) -> None:
        crop = (0.10, 0.20, 0.60, 0.80)
        np.testing.assert_allclose(
            rotate_crop(crop, 90),
            (0.20, 0.10, 0.80, 0.60),
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            rotate_crop(crop, 180),
            (0.40, 0.20, 0.90, 0.80),
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            rotate_crop(crop, 270),
            (0.20, 0.40, 0.80, 0.90),
            rtol=0.0,
            atol=1e-12,
        )

    def test_photo_state_keeps_independent_rotation(self) -> None:
        state = PhotoState(Path("scan.ARW"), rotation=450)
        self.assertEqual(state.rotation, 90)
        self.assertIn("90°", state.crop_label)

    def test_release_contains_fixed_output_rotation_and_quality(self) -> None:
        root = Path(__file__).resolve().parents[2]
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "plugin/manifest.json").read_text(encoding="utf-8"))
        patch = (root / "standalone/ps_sezhao/app_v057_rotate_output_patch.py").read_text(encoding="utf-8")
        launcher = (root / "standalone/main.py").read_text(encoding="utf-8")
        jobs = (root / "standalone/ps_sezhao/jobs.py").read_text(encoding="utf-8")

        self.assertEqual(version, "0.6.3")
        self.assertEqual(package["version"], version)
        self.assertEqual(manifest["version"], version)
        for token in (
            "左转 90°",
            "右转 90°",
            "输出（固定）",
            "JPEG 质量",
            'title in {"多图同步", "输出"}',
            "rotate_current",
            "rotate_crop",
            "jpeg_quality=quality",
        ):
            self.assertIn(token, patch)
        self.assertIn("apply_v057_rotate_output_patch", launcher)
        self.assertLess(jobs.index("rotate_array(image"), jobs.index("crop_array(image"))


if __name__ == "__main__":
    unittest.main()

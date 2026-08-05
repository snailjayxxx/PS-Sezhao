from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from ps_sezhao.workspace import (
    FULL_CROP,
    PhotoState,
    clamp_crop,
    crop_array,
    crop_is_full,
    crop_to_pixels,
    discover_images,
)


class WorkspaceTests(unittest.TestCase):
    def test_crop_clamps_and_orders_coordinates(self) -> None:
        crop = clamp_crop((0.9, 0.8, -0.2, 1.4))
        self.assertEqual(crop, (0.0, 0.8, 0.9, 1.0))

    def test_tiny_crop_returns_full_frame(self) -> None:
        self.assertEqual(clamp_crop((0.5, 0.5, 0.50001, 0.50001)), FULL_CROP)
        self.assertTrue(crop_is_full(FULL_CROP))

    def test_crop_array_uses_normalized_coordinates(self) -> None:
        image = np.arange(10 * 20 * 3, dtype=np.float32).reshape(10, 20, 3)
        result = crop_array(image, (0.25, 0.2, 0.75, 0.8))
        self.assertEqual(result.shape, (6, 10, 3))
        self.assertTrue(np.array_equal(result[0, 0], image[2, 5]))

    def test_crop_to_pixels_never_returns_empty_region(self) -> None:
        self.assertEqual(crop_to_pixels((3, 4, 3), (1, 1, 1, 1)), (0, 0, 4, 3))

    def test_discover_images_includes_raw_and_sorts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.JPG").write_bytes(b"x")
            (root / "a.tif").write_bytes(b"x")
            (root / "camera.NEF").write_bytes(b"x")
            (root / "negative.cr3").write_bytes(b"x")
            (root / "ignore.txt").write_text("x", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "scan.dng").write_bytes(b"x")
            direct = discover_images(root)
            recursive = discover_images(root, recursive=True)
            self.assertEqual(
                [path.name for path in direct],
                ["a.tif", "b.JPG", "camera.NEF", "negative.cr3"],
            )
            self.assertEqual(
                [path.name for path in recursive],
                ["a.tif", "b.JPG", "camera.NEF", "negative.cr3", "scan.dng"],
            )

    def test_photo_state_reports_crop_label(self) -> None:
        state = PhotoState(Path("sample.tif"), crop=(0.1, 0.2, 0.9, 0.8))
        self.assertEqual(state.crop_label, "80% × 60%")


if __name__ == "__main__":
    unittest.main()

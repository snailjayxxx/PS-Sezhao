from __future__ import annotations

import unittest

from ps_sezhao.crop_ui import map_view_point_to_source, update_crop_from_drag


class CropUiTests(unittest.TestCase):
    def test_visible_cropped_point_maps_back_to_original_source(self) -> None:
        source_shape = (1000, 2000, 3)
        view_shape = (500, 1000, 3)
        crop = (0.25, 0.20, 0.75, 0.70)
        left_top = map_view_point_to_source((0, 0), view_shape, source_shape, crop)
        right_bottom = map_view_point_to_source((999, 499), view_shape, source_shape, crop)
        self.assertAlmostEqual(left_top[0], 500, delta=1)
        self.assertAlmostEqual(left_top[1], 200, delta=1)
        self.assertAlmostEqual(right_bottom[0], 1499, delta=2)
        self.assertAlmostEqual(right_bottom[1], 699, delta=2)

    def test_corner_handle_resizes_existing_crop(self) -> None:
        crop = update_crop_from_drag(
            (0.2, 0.2, 0.8, 0.8),
            "nw",
            (0.2, 0.2),
            (0.1, 0.15),
        )
        self.assertEqual(crop, (0.1, 0.15, 0.8, 0.8))

    def test_move_keeps_size_and_stays_inside_image(self) -> None:
        crop = update_crop_from_drag(
            (0.7, 0.7, 0.95, 0.95),
            "move",
            (0.8, 0.8),
            (1.0, 1.0),
        )
        self.assertAlmostEqual(crop[2] - crop[0], 0.25)
        self.assertAlmostEqual(crop[3] - crop[1], 0.25)
        self.assertEqual(crop, (0.75, 0.75, 1.0, 1.0))

    def test_new_selection_is_ordered(self) -> None:
        crop = update_crop_from_drag(
            (0, 0, 1, 1),
            "new",
            (0.8, 0.7),
            (0.2, 0.1),
        )
        self.assertEqual(crop, (0.2, 0.1, 0.8, 0.7))


if __name__ == "__main__":
    unittest.main()

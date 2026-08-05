from __future__ import annotations

import unittest

import numpy as np

from ps_sezhao.color_profiles import PROPHOTO_RGB_V2_MICRO
from ps_sezhao.core.output import OutputSettings, prepare_output
from ps_sezhao.core.output_color_conversion import (
    prophoto_to_srgb,
    srgb_to_prophoto,
)


class OutputColorConversionTests(unittest.TestCase):
    def test_srgb_to_prophoto_changes_pixels_and_embeds_target_profile(self) -> None:
        image = np.asarray(
            [
                [[0.20, 0.35, 0.55], [0.70, 0.45, 0.25]],
                [[0.40, 0.40, 0.40], [0.15, 0.65, 0.35]],
            ],
            dtype=np.float32,
        )
        prepared = prepare_output(
            image,
            OutputSettings(color_space="prophoto"),
            source_icc_profile=None,
            source_metadata={},
        )
        self.assertEqual(prepared.icc_profile, PROPHOTO_RGB_V2_MICRO)
        self.assertFalse(np.allclose(prepared.image, image, atol=1e-4))
        self.assertTrue(np.isfinite(prepared.image).all())

    def test_float_round_trip_keeps_in_gamut_colors_close(self) -> None:
        srgb = np.asarray(
            [
                [[0.25, 0.30, 0.35], [0.55, 0.45, 0.30]],
                [[0.40, 0.55, 0.45], [0.70, 0.65, 0.60]],
            ],
            dtype=np.float32,
        )
        prophoto = srgb_to_prophoto(srgb)
        restored = prophoto_to_srgb(prophoto)
        np.testing.assert_allclose(restored, srgb, atol=2e-4, rtol=2e-4)

    def test_preserve_mode_does_not_change_pixels_or_profile(self) -> None:
        image = np.linspace(0.1, 0.9, 36, dtype=np.float32).reshape(3, 4, 3)
        profile = b"test-profile"
        prepared = prepare_output(
            image,
            OutputSettings(color_space="preserve"),
            source_icc_profile=profile,
            source_metadata={},
        )
        np.testing.assert_allclose(prepared.image, image)
        self.assertEqual(prepared.icc_profile, profile)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
import numpy as np

from ps_sezhao.engine import Controls, analyze_image, estimate_base_from_border, neutral_gains, process_image, sample_median_rgb


class EngineTests(unittest.TestCase):
    def make_negative(self) -> np.ndarray:
        height, width = 120, 160
        image = np.empty((height, width, 3), dtype=np.float32)
        image[:] = (0.92, 0.72, 0.43)
        yy, xx = np.mgrid[0:height, 0:width]
        inside = (xx > 14) & (xx < width - 15) & (yy > 12) & (yy < height - 13)
        image[inside, 0] = 0.70 - 0.35 * (xx[inside] / width)
        image[inside, 1] = 0.48 - 0.24 * (yy[inside] / height)
        image[inside, 2] = 0.25 - 0.10 * ((xx[inside] + yy[inside]) / (width + height))
        return np.clip(image, 0.01, 1.0)

    def test_border_analysis(self) -> None:
        image = self.make_negative()
        base, confidence = estimate_base_from_border(image, 0.1)
        self.assertGreater(base[0], base[1])
        self.assertGreater(base[1], base[2])
        self.assertGreater(confidence, 0.5)

    def test_process_returns_valid_rgb(self) -> None:
        image = self.make_negative()
        analysis = analyze_image(image, 0.1)
        result = process_image(image, analysis, Controls(profile="portra", exposure=0.5))
        self.assertEqual(result.shape, image.shape)
        self.assertEqual(result.dtype, np.float32)
        self.assertGreaterEqual(float(result.min()), 0.0)
        self.assertLessEqual(float(result.max()), 1.0)

    def test_temperature_changes_channel_balance(self) -> None:
        image = self.make_negative()
        analysis = analyze_image(image, 0.1)
        warm = process_image(image, analysis, Controls(temperature=2.0))
        cool = process_image(image, analysis, Controls(temperature=-2.0))
        self.assertGreater(float(warm[..., 0].mean()), float(cool[..., 0].mean()))
        self.assertLess(float(warm[..., 2].mean()), float(cool[..., 2].mean()))

    def test_patch_sampler(self) -> None:
        image = self.make_negative()
        sample = sample_median_rgb(image, 2, 2, 11)
        self.assertEqual(sample.shape, (3,))
        self.assertGreater(sample[0], sample[2])

    def test_neutral_gains_are_bounded(self) -> None:
        image = self.make_negative()
        analysis = analyze_image(image, 0.1)
        gains = neutral_gains(image, analysis, Controls(), 80, 60, 11)
        self.assertEqual(len(gains), 3)
        for value in gains:
            self.assertGreaterEqual(value, 0.25)
            self.assertLessEqual(value, 3.0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from ps_sezhao.jobs import run_job


ANALYSIS = {
    "base": [0.9, 0.7, 0.4],
    "black": [0.01, 0.01, 0.01],
    "white": [1.0, 1.0, 1.0],
    "confidence": 1.0,
    "method": "test",
}


class JobTests(unittest.TestCase):
    def test_each_item_uses_its_own_controls_analysis_and_crop(self) -> None:
        image = np.zeros((10, 20, 3), dtype=np.float32)
        captured: list[tuple[tuple[int, ...], float, float]] = []

        def fake_process(source, analysis, controls):
            captured.append((source.shape, controls.exposure, analysis.base[0]))
            return source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_path = root / "job.json"
            payload = {
                "settings": {
                    "controls": {"exposure": 0.0},
                    "analysis": ANALYSIS,
                    "crop": [0, 0, 1, 1],
                },
                "items": [
                    {
                        "input": str(root / "one.tif"),
                        "output": str(root / "one-out.tif"),
                        "controls": {"exposure": 0.5},
                        "analysis": {**ANALYSIS, "base": [0.8, 0.6, 0.3]},
                        "crop": [0.0, 0.0, 0.5, 1.0],
                    },
                    {
                        "input": str(root / "two.tif"),
                        "output": str(root / "two-out.tif"),
                        "controls": {"exposure": -0.25},
                        "analysis": {**ANALYSIS, "base": [0.95, 0.75, 0.45]},
                        "crop": [0.25, 0.2, 0.75, 0.8],
                    },
                ],
            }
            job_path.write_text(json.dumps(payload), encoding="utf-8")

            with patch("ps_sezhao.jobs.load_image", return_value=(image, {})), patch(
                "ps_sezhao.jobs.process_image_tiled", side_effect=fake_process
            ), patch("ps_sezhao.jobs.save_image"):
                outputs = run_job(job_path)

        self.assertEqual(len(outputs), 2)
        self.assertEqual(captured[0], ((10, 10, 3), 0.5, 0.8))
        self.assertEqual(captured[1], ((6, 10, 3), -0.25, 0.95))


if __name__ == "__main__":
    unittest.main()

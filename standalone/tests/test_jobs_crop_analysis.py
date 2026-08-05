from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from ps_sezhao.engine import Analysis
from ps_sezhao.jobs import run_job


class JobCropAnalysisTests(unittest.TestCase):
    def test_missing_analysis_uses_cropped_source(self) -> None:
        image = np.zeros((10, 20, 3), dtype=np.float32)
        analyzed_shapes: list[tuple[int, ...]] = []
        processed_shapes: list[tuple[int, ...]] = []

        def fake_analyze(source, **_kwargs):
            analyzed_shapes.append(source.shape)
            return Analysis(
                base=(0.9, 0.7, 0.4),
                black=(0.0, 0.0, 0.0),
                white=(1.0, 1.0, 1.0),
                method="crop-border",
            )

        def fake_process(source, _analysis, _controls):
            processed_shapes.append(source.shape)
            return source

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job_path = root / "job.json"
            job_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "input": str(root / "source.tif"),
                                "output": str(root / "result.tif"),
                                "crop": [0.25, 0.2, 0.75, 0.8],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch("ps_sezhao.jobs.load_image", return_value=(image, {})), patch(
                "ps_sezhao.jobs.analyze_image", side_effect=fake_analyze
            ), patch("ps_sezhao.jobs.process_image_tiled", side_effect=fake_process), patch(
                "ps_sezhao.jobs.save_image"
            ):
                run_job(job_path)

        self.assertEqual(analyzed_shapes, [(6, 10, 3)])
        self.assertEqual(processed_shapes, [(6, 10, 3)])


if __name__ == "__main__":
    unittest.main()

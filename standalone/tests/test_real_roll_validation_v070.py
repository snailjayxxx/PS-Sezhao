from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from ps_sezhao.validation import validate_real_roll


class RealRollValidationTests(unittest.TestCase):
    def test_validator_produces_non_destructive_reports_and_review_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "胶卷 测试"
            sources.mkdir()
            originals: dict[Path, bytes] = {}
            for index in range(2):
                path = sources / f"负片-{index + 1}.png"
                image = Image.new("RGB", (240, 160), (228, 150, 82))
                draw = ImageDraw.Draw(image)
                draw.rectangle((24, 18, 216, 142), fill=(86 + index * 8, 60, 42))
                draw.ellipse((72, 42, 168, 132), fill=(150, 100 + index * 6, 66))
                image.save(path)
                originals[path] = path.read_bytes()

            output = root / "report"
            report = validate_real_roll(
                [sources],
                output,
                recursive=True,
                full_decode=True,
            )
            json_path = report.write_json(output / "real-roll-report.json")
            markdown_path = report.write_markdown(output / "real-roll-report.md")

            self.assertTrue(report.ok)
            self.assertEqual(report.total, 2)
            self.assertEqual(report.succeeded, 2)
            self.assertEqual(report.failed, 0)
            self.assertTrue(json_path.is_file())
            self.assertTrue(markdown_path.is_file())
            self.assertIn("PS-Sezhao 真实胶卷验证报告", markdown_path.read_text(encoding="utf-8"))
            for item in report.items:
                self.assertIsNone(item.error)
                self.assertIsNotNone(item.review_image)
                self.assertTrue(Path(item.review_image or "").is_file())
                self.assertIsNotNone(item.full_shape)
                self.assertGreaterEqual(item.output_max or 0.0, item.output_min or 0.0)
            for path, before in originals.items():
                self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

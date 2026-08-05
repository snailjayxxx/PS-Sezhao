from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from ps_sezhao import engine
from ps_sezhao.engine_style_v060_patch import (
    FILM_PROFILE_ORDER,
    FILM_PROFILES,
    SCANNER_PROFILE_ORDER,
    SCANNER_PROFILES,
    apply_style_engine_patch,
)
from ps_sezhao.engine_v053_patch import apply_engine_patch

apply_engine_patch()
apply_style_engine_patch()


class StyleLibraryV060Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = engine.Analysis(
            base=(0.92, 0.64, 0.38),
            black=(0.0, 0.0, 0.0),
            white=(1.25, 1.20, 1.15),
        )
        self.image = np.asarray([[[0.42, 0.28, 0.16]]], dtype=np.float32)

    def test_scanner_and_film_are_independent(self) -> None:
        neutral = engine.Controls(profile="generic")
        neutral.scanner_profile = "neutral_lab"
        neutral.scanner_strength = 1.0

        scanner_only = engine.Controls(profile="generic")
        scanner_only.scanner_profile = "hasselblad_flextight_x5"
        scanner_only.scanner_strength = 1.0

        film_only = engine.Controls(profile="kodak_portra_400")
        film_only.scanner_profile = "neutral_lab"
        film_only.scanner_strength = 1.0

        neutral_result = engine.process_image(self.image, self.analysis, neutral)
        scanner_result = engine.process_image(self.image, self.analysis, scanner_only)
        film_result = engine.process_image(self.image, self.analysis, film_only)

        self.assertFalse(np.allclose(neutral_result, scanner_result))
        self.assertFalse(np.allclose(neutral_result, film_result))
        self.assertFalse(np.allclose(scanner_result, film_result))

    def test_zero_strength_disables_each_style_independently(self) -> None:
        neutral = engine.Controls(profile="generic", style_strength=0.0)
        neutral.scanner_profile = "neutral_lab"
        neutral.scanner_strength = 0.0

        styled = engine.Controls(profile="kodak_ektar_100", style_strength=0.0)
        styled.scanner_profile = "frontier_sp3000_vivid"
        styled.scanner_strength = 0.0

        np.testing.assert_allclose(
            engine.process_image(self.image, self.analysis, neutral),
            engine.process_image(self.image, self.analysis, styled),
            rtol=0.0,
            atol=1e-7,
        )

    def test_saved_controls_keep_scanner_fields_and_migrate_legacy_film_names(self) -> None:
        controls = engine.Controls.from_dict(
            {
                "profile": "portra",
                "styleStrength": 0.8,
                "scannerProfile": "noritsu_hs1800",
                "scannerStrength": 1.25,
            }
        )
        payload = controls.to_dict()
        self.assertEqual(payload["profile"], "kodak_portra_400")
        self.assertEqual(payload["scanner_profile"], "noritsu_hs1800")
        self.assertAlmostEqual(payload["scanner_strength"], 1.25)

    def test_first_library_contains_requested_popular_names(self) -> None:
        self.assertEqual(len(SCANNER_PROFILE_ORDER), 6)
        self.assertEqual(len(FILM_PROFILE_ORDER), 16)
        scanner_labels = "\n".join(str(SCANNER_PROFILES[key]["label"]) for key in SCANNER_PROFILE_ORDER)
        film_labels = "\n".join(str(FILM_PROFILES[key]["label"]) for key in FILM_PROFILE_ORDER)
        for name in ("Hasselblad Flextight X5", "Noritsu HS-1800", "Frontier SP-3000"):
            self.assertIn(name, scanner_labels)
        for name in (
            "Kodak Portra 400",
            "Kodak Gold 200",
            "Kodak Ektar 100",
            "Fujifilm Pro 400H",
            "CineStill 800T",
            "Ilford HP5 Plus 400",
        ):
            self.assertIn(name, film_labels)

    def test_release_wires_style_library_into_all_high_precision_paths(self) -> None:
        root = Path(__file__).resolve().parents[2]
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "plugin/manifest.json").read_text(encoding="utf-8"))
        launcher = (root / "standalone/main.py").read_text(encoding="utf-8")
        runtime = (root / "plugin/runtime-v022.js").read_text(encoding="utf-8")
        html = (root / "plugin/index.html").read_text(encoding="utf-8")

        self.assertEqual(version, "0.6.0")
        self.assertEqual(package["version"], version)
        self.assertEqual(manifest["version"], version)
        self.assertIn("apply_style_engine_patch", launcher)
        self.assertIn("apply_v060_style_library_patch", launcher)
        self.assertIn("source_crop_module.neutral_gains = engine_module.neutral_gains", launcher)
        self.assertIn('require("./runtime-engine-style-v060.js")', runtime)
        self.assertIn('require("./runtime-style-v060.js")', runtime)
        self.assertIn('id="scannerProfile"', html)
        self.assertIn('id="profile"', html)
        self.assertIn("非官方风格参考", html)


if __name__ == "__main__":
    unittest.main()

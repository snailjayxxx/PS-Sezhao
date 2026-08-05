from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from ps_sezhao.bootstrap import configure_application
from ps_sezhao.core.lut import apply_cube_lut, load_cube_lut
from ps_sezhao.storage import paths


IDENTITY_CUBE = """TITLE \"Identity 2\"
LUT_3D_SIZE 2
DOMAIN_MIN 0 0 0
DOMAIN_MAX 1 1 1
0 0 0
1 0 0
0 1 0
1 1 0
0 0 1
1 0 1
0 1 1
1 1 1
"""

INVERT_CUBE = """TITLE \"Invert\"
LUT_1D_SIZE 2
1 1 1
0 0 0
"""


class LutAndPortablePathsV072Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configure_application()

    def test_cube_lut_uses_identity_trilinear_interpolation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "identity.cube"
            source.write_text(IDENTITY_CUBE, encoding="utf-8")
            lut = load_cube_lut(source)
            image = np.asarray(
                [[[0.1, 0.2, 0.3], [0.9, 0.4, 0.7]]],
                dtype=np.float32,
            )
            result = apply_cube_lut(image, lut)
            np.testing.assert_allclose(result, image, atol=1e-6)
            self.assertEqual(lut.dimension, 3)
            self.assertEqual(lut.size, 2)

    def test_controls_round_trip_and_processing_apply_user_lut(self) -> None:
        from ps_sezhao import engine

        with tempfile.TemporaryDirectory() as temporary_directory, patch.dict(
            os.environ,
            {paths.ENV_DATA_ROOT: temporary_directory},
            clear=False,
        ):
            lut_directory = paths.default_lut_directory()
            source = lut_directory / "invert.cube"
            source.write_text(INVERT_CUBE, encoding="utf-8")

            controls = engine.Controls.from_dict(
                {
                    "profile": "generic",
                    "style_strength": 1.0,
                    "user_lut": source.name,
                }
            )
            self.assertEqual(controls.to_dict()["user_lut"], source.name)

            image = np.asarray([[[0.80, 0.55, 0.25]]], dtype=np.float32)
            analysis = engine.Analysis(
                base=(1.0, 1.0, 1.0),
                black=(0.0, 0.0, 0.0),
                white=(2.0, 2.0, 2.0),
            )
            plain = engine.process_image(image, analysis, engine.Controls())
            transformed = engine.process_image(image, analysis, controls)
            np.testing.assert_allclose(transformed, 1.0 - plain, atol=2e-5)

    def test_project_database_moves_to_project_folder_and_keeps_legacy_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            legacy = root / "legacy" / "workspace.sqlite3"
            legacy.parent.mkdir(parents=True)
            with sqlite3.connect(legacy) as connection:
                connection.execute("CREATE TABLE sample(value TEXT)")
                connection.execute("INSERT INTO sample(value) VALUES('kept')")

            with patch.dict(
                os.environ,
                {paths.ENV_DATA_ROOT: str(root / "portable")},
                clear=False,
            ), patch.object(paths, "legacy_project_database_path", return_value=legacy):
                target = paths.default_project_database_path()

            self.assertEqual(target.parent.name, "project")
            self.assertTrue(target.is_file())
            self.assertTrue(legacy.is_file())
            with sqlite3.connect(target) as connection:
                value = connection.execute("SELECT value FROM sample").fetchone()[0]
            self.assertEqual(value, "kept")
            self.assertTrue((target.parent.parent / "lut").is_dir())
            self.assertTrue((target.parent / "MIGRATED_FROM.txt").is_file())


if __name__ == "__main__":
    unittest.main()

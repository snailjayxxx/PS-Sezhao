from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ps_sezhao import startup_guard
from ps_sezhao.storage import paths


class StartupGuardV074Tests(unittest.TestCase):
    def test_first_run_creates_all_support_folders_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory, patch.dict(
            os.environ,
            {paths.ENV_DATA_ROOT: temporary_directory},
            clear=False,
        ):
            log_path = startup_guard.initialize_startup_environment()
            root = Path(temporary_directory)
            self.assertEqual(log_path, root / "logs" / "startup.log")
            self.assertTrue((root / "project").is_dir())
            self.assertTrue((root / "lut").is_dir())
            self.assertTrue((root / "logs").is_dir())
            self.assertTrue(log_path.is_file())
            self.assertIn("PS-Sezhao startup begin", log_path.read_text(encoding="utf-8"))

    def test_guard_records_pre_window_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory, patch.dict(
            os.environ,
            {paths.ENV_DATA_ROOT: temporary_directory},
            clear=False,
        ), patch.object(startup_guard, "_show_startup_error") as show_error:
            def failing_application(_argv=None):
                raise RuntimeError("startup failed for test")

            result = startup_guard.run_guarded(failing_application)
            log_path = Path(temporary_directory) / "logs" / "startup.log"
            self.assertEqual(result, 1)
            self.assertTrue(log_path.is_file())
            self.assertIn("startup failed for test", log_path.read_text(encoding="utf-8"))
            show_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()

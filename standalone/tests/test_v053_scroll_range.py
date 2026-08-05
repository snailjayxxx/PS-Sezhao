from __future__ import annotations

from types import SimpleNamespace
import unittest

from ps_sezhao.app_v053_scroll_patch import _wheel_units
from ps_sezhao.engine import Controls
from ps_sezhao.engine_v053_patch import apply_engine_patch


class V053RangeAndScrollTests(unittest.TestCase):
    def setUp(self) -> None:
        apply_engine_patch()

    def test_base_adjust_accepts_extended_normalized_range(self) -> None:
        controls = Controls(base_adjust=(-2.0, 0.5, 2.0)).sanitized()
        self.assertEqual(controls.base_adjust, (-1.5, 0.5, 1.5))

    def test_windows_wheel_direction(self) -> None:
        self.assertEqual(_wheel_units(SimpleNamespace(delta=120)), -1)
        self.assertEqual(_wheel_units(SimpleNamespace(delta=-120)), 1)

    def test_macos_small_wheel_delta(self) -> None:
        self.assertEqual(_wheel_units(SimpleNamespace(delta=1)), -1)
        self.assertEqual(_wheel_units(SimpleNamespace(delta=-1)), 1)

    def test_x11_button_direction(self) -> None:
        self.assertEqual(_wheel_units(SimpleNamespace(delta=0), 1), -1)
        self.assertEqual(_wheel_units(SimpleNamespace(delta=0), -1), 1)


if __name__ == "__main__":
    unittest.main()

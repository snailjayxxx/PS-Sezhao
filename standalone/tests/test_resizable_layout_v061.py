from __future__ import annotations

import unittest
from pathlib import Path

from ps_sezhao.app_v061_resizable_layout_patch import (
    CONTROLS_MIN_WIDTH,
    LIST_MIN_WIDTH,
    PREVIEW_MIN_WIDTH,
    initial_sash_positions,
)


class ResizableLayoutV061Tests(unittest.TestCase):
    def test_initial_sashes_keep_three_usable_panes(self) -> None:
        for width in (1080, 1460, 1920, 2560):
            left, right = initial_sash_positions(width)
            self.assertGreaterEqual(left, LIST_MIN_WIDTH)
            self.assertGreaterEqual(right - left, PREVIEW_MIN_WIDTH)
            self.assertGreaterEqual(width - right, CONTROLS_MIN_WIDTH)
            self.assertLess(left, right)

    def test_layout_patch_replaces_fixed_width_controls(self) -> None:
        root = Path(__file__).resolve().parents[2]
        patch = (
            root / "standalone/ps_sezhao/app_v061_resizable_layout_patch.py"
        ).read_text(encoding="utf-8")
        launcher = (root / "standalone/main.py").read_text(encoding="utf-8")

        for token in (
            "tk.PanedWindow",
            "sashwidth=SASH_WIDTH",
            "showhandle=True",
            'stretch="always"',
            "canvas.itemconfigure(window_item, width=width)",
            "controls_canvas.configure(width=1)",
            "widget.configure(wraplength=wraplength)",
        ):
            self.assertIn(token, patch)
        self.assertIn("apply_v061_resizable_layout_patch", launcher)


if __name__ == "__main__":
    unittest.main()

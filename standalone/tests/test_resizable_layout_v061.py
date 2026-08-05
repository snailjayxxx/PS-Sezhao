from __future__ import annotations

import unittest
from pathlib import Path

from ps_sezhao.app_v061_resizable_layout_patch import (
    CONTROLS_MIN_WIDTH,
    LIST_MIN_WIDTH,
    PREVIEW_MIN_WIDTH,
    clamp_sash_positions,
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

    def test_dragged_sashes_are_only_clamped_at_minimum_widths(self) -> None:
        width = 1460
        for left, right in ((20, 1400), (300, 500), (500, 1400), (260, 1080)):
            safe_left, safe_right = clamp_sash_positions(width, left, right)
            self.assertGreaterEqual(safe_left, LIST_MIN_WIDTH)
            self.assertGreaterEqual(safe_right - safe_left, PREVIEW_MIN_WIDTH)
            self.assertGreaterEqual(width - safe_right, CONTROLS_MIN_WIDTH)

    def test_layout_patch_keeps_existing_widgets_alive(self) -> None:
        root = Path(__file__).resolve().parents[2]
        patch = (
            root / "standalone/ps_sezhao/app_v061_resizable_layout_patch.py"
        ).read_text(encoding="utf-8")
        groups = (root / "standalone/ps_sezhao/integration_groups.py").read_text(encoding="utf-8")

        for token in (
            "_configure_existing_three_pane_layout",
            "isinstance(child, ttk.Panedwindow)",
            "body.pane(pane, weight=weight)",
            "body.sashpos(0, left)",
            "canvas.itemconfigure(window_item, width=width)",
            "controls_canvas.configure(width=1)",
            "widget.configure(wraplength=wraplength)",
            "clamp_sash_positions",
        ):
            self.assertIn(token, patch)

        self.assertNotIn("old_body.destroy()", patch)
        self.assertNotIn("self._build_controls_panel(controls_outer)", patch)
        self.assertIn("apply_v061_resizable_layout_patch", groups)


if __name__ == "__main__":
    unittest.main()

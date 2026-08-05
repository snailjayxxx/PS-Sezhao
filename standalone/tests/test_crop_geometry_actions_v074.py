from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from tkinter import ttk

from ps_sezhao.core.geometry import GeometrySettings
from ps_sezhao.ui import create_application, create_root
from ps_sezhao.workspace import FULL_CROP, PhotoState


class CropGeometryActionBindingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.error_dialog_patcher = patch(
            "ps_sezhao.services.ui_action_bindings.messagebox.showerror"
        )
        self.error_dialog = self.error_dialog_patcher.start()
        self.root = create_root()
        self.root.geometry("1500x900")
        self.root.withdraw()
        self.app = create_application(self.root)
        self.root.update_idletasks()

    def tearDown(self) -> None:
        self.root.destroy()
        self.error_dialog_patcher.stop()

    def test_crop_control_restores_the_complete_crop_entry(self) -> None:
        self.assertTrue(self.app._ui_action_bindings_applied)
        crop_group = self.app._v072_tool_groups[0]
        texts = tuple(
            str(widget.cget("text"))
            for widget in crop_group.winfo_children()
            if isinstance(widget, ttk.Button)
        )
        self.assertEqual(texts, ("裁切", "重置裁切"))
        self.assertFalse(
            any(isinstance(widget, ttk.Radiobutton) for widget in crop_group.winfo_children())
        )

        image = np.zeros((40, 60, 3), dtype=np.float32)
        image[5:35, 10:50] = (0.8, 0.4, 0.2)
        self.app.preview_source = image.copy()
        self.app.preview_result = image.copy()
        self.app.crop_norm = FULL_CROP
        self.app._set_display_image(image)
        self.root.update_idletasks()

        self.app.crop_toggle_button.invoke()
        self.root.update_idletasks()
        self.app.draw_preview()

        self.error_dialog.assert_not_called()
        self.assertTrue(self.app.crop_editing)
        self.assertEqual(self.app.interaction_mode.get(), "crop")
        self.assertEqual(str(self.app.crop_toggle_button.cget("text")), "完成裁切")
        self.assertIn("裁切编辑", self.app.status.get())
        self.assertGreater(len(self.app.canvas.find_all()), 1)

    def test_visible_rotation_and_flip_buttons_call_the_final_services(self) -> None:
        item = PhotoState(
            Path("synthetic.tif"),
            crop=FULL_CROP,
            rotation=0,
            geometry=GeometrySettings().to_dict(),
        )
        self.app.items = [item]
        self.app.current_index = 0
        source = np.arange(3 * 5 * 3, dtype=np.float32).reshape(3, 5, 3) / 45.0
        self.app.preview_source = source.copy()
        self.app.preview_result = source.copy()
        self.app.crop_norm = FULL_CROP

        self.app._store_current_state = lambda: None
        self.app._refresh_after_rotation = lambda: None
        self.app._refresh_geometry_preview = lambda: None
        self.app._record_history = lambda *args, **kwargs: None
        self.app.schedule_render = lambda *args, **kwargs: None

        self.app.rotate_right_button.invoke()
        self.error_dialog.assert_not_called()
        self.assertEqual(item.rotation, 90)
        self.assertEqual(self.app.preview_source.shape[:2], (5, 3))
        self.assertIn("90°", self.app.status.get())

        self.app.horizontal_flip_button.invoke()
        self.error_dialog.assert_not_called()
        horizontal = GeometrySettings.from_dict(item.geometry)
        self.assertTrue(horizontal.flip_horizontal)
        self.assertFalse(horizontal.flip_vertical)
        self.assertIn("水平翻转", self.app.status.get())

        self.app.vertical_flip_button.invoke()
        self.error_dialog.assert_not_called()
        both = GeometrySettings.from_dict(item.geometry)
        self.assertTrue(both.flip_horizontal)
        self.assertTrue(both.flip_vertical)
        self.assertIn("垂直翻转", self.app.status.get())

    def test_buttons_resolve_methods_at_click_time(self) -> None:
        calls: list[tuple[str, object]] = []
        self.app.toggle_crop_editing = lambda: calls.append(("crop", None))
        self.app.rotate_current = lambda degrees: calls.append(("rotate", degrees))
        self.app.toggle_flip = lambda direction: calls.append(("flip", direction))

        self.app.crop_toggle_button.invoke()
        self.app.rotate_left_button.invoke()
        self.app.rotate_right_button.invoke()
        self.app.horizontal_flip_button.invoke()
        self.app.vertical_flip_button.invoke()

        self.error_dialog.assert_not_called()
        self.assertEqual(
            calls,
            [
                ("crop", None),
                ("rotate", -90),
                ("rotate", 90),
                ("flip", "horizontal"),
                ("flip", "vertical"),
            ],
        )


if __name__ == "__main__":
    unittest.main()

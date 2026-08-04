from __future__ import annotations

from typing import Any, Type

from .workspace import FULL_CROP


def apply_patch(app_class: Type[Any]) -> None:
    """Apply v0.5.0 interaction fixes without coupling the UI to the launcher.

    The first v0.5.0 crop implementation updated the crop rectangle during the
    mouse-press event. A click without movement therefore produced a zero-area
    rectangle which was normalized back to the full frame. This patch keeps the
    previous crop until the pointer actually moves.
    """

    if getattr(app_class, "_v050_crop_patch_applied", False):
        return

    original_motion = app_class.on_canvas_motion
    original_release = app_class.on_canvas_release

    def on_canvas_press(self: Any, event: Any) -> None:
        point = self.map_canvas_to_preview(event.x, event.y)
        if self.pick_mode:
            if point is not None:
                self._apply_pick(round(point[0]), round(point[1]))
            return
        if self.preview_source is None:
            return
        if self.interaction_mode.get() == "crop":
            if point is None:
                return
            self.drag_origin = point
            self.crop_before_drag = self.crop_norm
            self.crop_dragged = False
        else:
            self.pan_origin = (float(event.x), float(event.y), self.pan_x, self.pan_y)
            self.canvas.configure(cursor="fleur")

    def on_canvas_motion(self: Any, event: Any) -> None:
        if self.drag_origin is not None and self.interaction_mode.get() == "crop":
            self.crop_dragged = True
        original_motion(self, event)

    def on_canvas_release(self: Any, event: Any) -> None:
        if self.drag_origin is not None and not getattr(self, "crop_dragged", False):
            self.crop_norm = getattr(self, "crop_before_drag", FULL_CROP)
        original_release(self, event)
        self.crop_dragged = False

    app_class.on_canvas_press = on_canvas_press
    app_class.on_canvas_motion = on_canvas_motion
    app_class.on_canvas_release = on_canvas_release
    app_class._v050_crop_patch_applied = True

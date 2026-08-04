from __future__ import annotations

import json
import threading
from typing import Any, Type

from tkinter import messagebox

from .jobs import run_job
from .workspace import FULL_CROP, clamp_crop


def apply_patch(app_class: Type[Any]) -> None:
    """Apply v0.5.0 interaction and Lightroom multi-photo fixes.

    The crop guard keeps an existing crop when the user clicks without dragging.
    The Lightroom job override serializes each photo's own analysis, controls and
    crop instead of applying only the currently visible photo's settings to all.
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

    def run_lr_job(self: Any) -> None:
        if self.lr_job_data is None or self.lr_job_path is None:
            return
        self._store_current_state()
        job_items = self.lr_job_data.get("items") or []
        if not job_items:
            messagebox.showinfo("Lightroom 任务为空", "当前 Lightroom 任务中没有照片。")
            return

        for index, job_item in enumerate(job_items):
            if index >= len(self.items):
                break
            state = self.items[index]
            if state.analysis:
                job_item["analysis"] = dict(state.analysis)
            if state.controls:
                job_item["controls"] = dict(state.controls)
            job_item["crop"] = list(clamp_crop(state.crop))

        self.lr_job_data.setdefault("settings", {})["multi_photo"] = True
        self.lr_job_path.write_text(
            json.dumps(self.lr_job_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.status.set("正在按每张照片的独立参数生成 Lightroom 正片…")

        def progress(done: int, total: int, name: str) -> None:
            self.root.after(0, lambda: self.status.set(f"Lightroom 批量处理 {done}/{total}：{name}"))

        def worker() -> None:
            try:
                run_job(self.lr_job_path, progress)
                self.root.after(0, self._finish_lr_job)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("Lightroom 处理失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    app_class.on_canvas_press = on_canvas_press
    app_class.on_canvas_motion = on_canvas_motion
    app_class.on_canvas_release = on_canvas_release
    app_class._run_lr_job = run_lr_job
    app_class._v050_crop_patch_applied = True

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Type

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .crop_ui import map_view_point_to_source, normalized_point, update_crop_from_drag
from .engine import Analysis, Controls, analyze_image, neutral_gains, sample_median_rgb
from .io_utils import load_image, make_preview, save_image
from .processing import process_image_tiled
from .raw_io import prepare_save_output
from .workspace import FULL_CROP, clamp_crop, crop_array, crop_is_full

BASE_CHANNELS = (("R", 0), ("G", 1), ("B", 2))


def apply_source_crop_patch(app_class: Type[Any]) -> None:
    """Apply v0.5.2 source sampling, manual base and crop-view behavior."""

    if getattr(app_class, "_v052_source_crop_patch_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_preview_panel = app_class._build_preview_panel
    original_build_controls_panel = app_class._build_controls_panel
    original_controls_value = app_class.controls_value
    original_apply_controls = app_class.apply_controls
    original_set_display_image = app_class._set_display_image
    original_map_canvas_to_preview = app_class.map_canvas_to_preview
    original_on_canvas_press = app_class.on_canvas_press
    original_on_canvas_motion = app_class.on_canvas_motion
    original_on_canvas_release = app_class.on_canvas_release
    original_load_index = app_class.load_index
    original_clear_current_display = app_class._clear_current_display

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.crop_editing = False
        self.crop_drag_mode: str | None = None
        self.crop_drag_start = (0.0, 0.0)
        self.crop_drag_initial = FULL_CROP
        self._display_full_array: np.ndarray | None = None
        self._display_view_array: np.ndarray | None = None
        self._display_source_crop = FULL_CROP
        self.crop_toggle_button: ttk.Button | None = None
        self.base_adjust_units = {
            channel: tk.DoubleVar(value=0.0) for channel, _index in BASE_CHANNELS
        }
        self.base_adjust_entries = {
            channel: tk.StringVar(value="0") for channel, _index in BASE_CHANNELS
        }
        self.base_value_text = tk.StringVar(value="等待分析胶片基底")

    def build_preview_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_preview_panel(self, parent)
        children = parent.winfo_children()
        viewbar = next((child for child in children if isinstance(child, ttk.Frame)), None)
        if viewbar is not None:
            for child in viewbar.winfo_children():
                try:
                    text = str(child.cget("text"))
                except Exception:
                    text = ""
                if text in {"平移", "裁切"}:
                    child.grid_remove()
            self.crop_toggle_button = ttk.Button(viewbar, text="裁切", command=self.toggle_crop_editing)
            self.crop_toggle_button.grid(row=0, column=1, columnspan=2, padx=(0, 4))
        labels = [child for child in children if isinstance(child, ttk.Label)]
        if labels:
            labels[-1].configure(
                text="平时只显示裁切后的画面。点击“裁切”进入全图编辑；拖动边框、角点或框内区域，完成后再次点击按钮。"
            )

    def build_controls_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_controls_panel(self, parent)
        row = self.controls.grid_size()[1]
        frame = ttk.LabelFrame(self.controls, text="胶片基底手动微调 · v0.5.2", padding=7)
        frame.grid(row=row, column=0, sticky="ew", pady=(2, 12))
        frame.columnconfigure(0, weight=1)
        ttk.Label(
            frame,
            textvariable=self.base_value_text,
            foreground="#555",
            wraplength=295,
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))

        for row_index, (channel, _index) in enumerate(BASE_CHANNELS, start=1):
            line = ttk.Frame(frame)
            line.grid(row=row_index, column=0, sticky="ew", pady=2)
            line.columnconfigure(1, weight=1)
            ttk.Label(line, text=f"基底 {channel}", width=7).grid(row=0, column=0, sticky="w")
            scale = tk.Scale(
                line,
                from_=-64,
                to=64,
                resolution=1,
                orient=tk.HORIZONTAL,
                showvalue=False,
                highlightthickness=0,
                variable=self.base_adjust_units[channel],
                command=lambda _value, c=channel: self.on_base_scale(c),
            )
            scale.grid(row=0, column=1, sticky="ew")
            stepper = ttk.Frame(line)
            stepper.grid(row=0, column=2, sticky="e", padx=(5, 0))
            ttk.Button(stepper, text="−", width=3, command=lambda c=channel: self.adjust_base(c, -1)).grid(row=0, column=0)
            entry = ttk.Entry(stepper, textvariable=self.base_adjust_entries[channel], width=6, justify="right")
            entry.grid(row=0, column=1, padx=2)
            ttk.Button(stepper, text="+", width=3, command=lambda c=channel: self.adjust_base(c, 1)).grid(row=0, column=2)
            entry.bind("<Return>", lambda _event, c=channel: self.commit_base_entry(c))
            entry.bind("<FocusOut>", lambda _event, c=channel: self.commit_base_entry(c))
            entry.bind("<Up>", lambda _event, c=channel: self.adjust_base(c, 1))
            entry.bind("<Down>", lambda _event, c=channel: self.adjust_base(c, -1))

        ttk.Button(frame, text="重置胶片基底微调", command=self.reset_base_adjust).grid(
            row=4, column=0, sticky="ew", pady=(6, 2)
        )
        ttk.Label(
            frame,
            text="数值是相对原图吸管/自动分析结果的 8 位等效偏移。Photoshop 版同样位于“胶片基底微调”；Lightroom 高精度窗口复用此面板。",
            foreground="#666",
            wraplength=295,
        ).grid(row=5, column=0, sticky="w", pady=(3, 0))
        self.update_base_value_text()

    def controls_value(self: Any) -> Controls:
        controls = original_controls_value(self)
        payload = controls.to_dict()
        payload["base_adjust"] = tuple(
            float(self.base_adjust_units[channel].get()) / 255.0 for channel, _index in BASE_CHANNELS
        )
        return Controls.from_dict(payload)

    def apply_controls(self: Any, controls: Controls) -> None:
        original_apply_controls(self, controls)
        old_loading = getattr(self, "_loading_item", False)
        self._loading_item = True
        try:
            for (channel, index), value in zip(BASE_CHANNELS, controls.base_adjust):
                units = round(float(value) * 255.0)
                self.base_adjust_units[channel].set(units)
                self.base_adjust_entries[channel].set(str(units))
        finally:
            self._loading_item = old_loading
        self.update_base_value_text()

    def on_base_scale(self: Any, channel: str) -> None:
        value = round(float(self.base_adjust_units[channel].get()))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()

    def commit_base_entry(self: Any, channel: str) -> str:
        try:
            value = float(self.base_adjust_entries[channel].get().strip())
        except (TypeError, ValueError):
            value = float(self.base_adjust_units[channel].get())
        value = round(min(64.0, max(-64.0, value)))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()
        return "break"

    def adjust_base(self: Any, channel: str, direction: int) -> str:
        value = round(float(self.base_adjust_units[channel].get()) + int(direction))
        value = min(64, max(-64, value))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()
        return "break"

    def reset_base_adjust(self: Any) -> None:
        for channel, _index in BASE_CHANNELS:
            self.base_adjust_units[channel].set(0)
            self.base_adjust_entries[channel].set("0")
        self.base_adjust_changed()

    def base_adjust_changed(self: Any) -> None:
        if getattr(self, "_loading_item", False):
            return
        self.update_base_value_text()
        self._control_changed()

    def update_base_value_text(self: Any) -> None:
        if self.analysis is None:
            self.base_value_text.set("等待分析胶片基底")
            return
        measured = np.asarray(self.analysis.base, dtype=np.float32)
        offsets = np.asarray(
            [self.base_adjust_units[channel].get() / 255.0 for channel, _index in BASE_CHANNELS],
            dtype=np.float32,
        )
        current = np.clip(measured + offsets, 0.0, 1.5)
        original_text = " / ".join(str(round(float(value) * 255.0)) for value in measured)
        current_text = " / ".join(str(round(float(value) * 255.0)) for value in current)
        self.base_value_text.set(f"原图识别 R/G/B：{original_text}　→　当前基底：{current_text}")

    def set_display_image(self: Any, image: Any | None) -> None:
        if image is None:
            self._display_full_array = None
            self._display_view_array = None
            self._display_source_crop = FULL_CROP
            original_set_display_image(self, None)
            return
        self._display_full_array = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0).copy()
        self.refresh_crop_display()

    def refresh_crop_display(self: Any) -> None:
        if self._display_full_array is None:
            original_set_display_image(self, None)
            return
        if self.crop_editing or self.preview_source is None or crop_is_full(self.crop_norm):
            shown = self._display_full_array
            self._display_source_crop = FULL_CROP
        else:
            shown = crop_array(self._display_full_array, self.crop_norm)
            self._display_source_crop = clamp_crop(self.crop_norm)
        self._display_view_array = shown
        original_set_display_image(self, shown)

    def map_canvas_to_preview(self: Any, canvas_x: float, canvas_y: float) -> tuple[float, float] | None:
        point = original_map_canvas_to_preview(self, canvas_x, canvas_y)
        if point is None or self.preview_source is None or self._display_view_array is None:
            return point
        if crop_is_full(self._display_source_crop):
            return point
        return map_view_point_to_source(
            point,
            self._display_view_array.shape,
            self.preview_source.shape,
            self._display_source_crop,
        )

    def analysis_source(self: Any) -> np.ndarray:
        if self.preview_source is None:
            raise ValueError("尚未载入可分析的原图预览。")
        return crop_array(self.preview_source, self.crop_norm)

    def auto_analyze(self: Any) -> None:
        if self.preview_source is None:
            return
        try:
            self.status.set("正在裁切范围内分析胶片边框…")
            self.analysis = analyze_image(self.analysis_source(), border_fraction=0.07, method="crop-border")
            self._store_current_state()
            self.update_base_value_text()
            self.status.set(f"裁切范围内基底分析完成，可信度 {self.analysis.confidence * 100:.0f}%")
            self.schedule_render(0)
        except Exception as error:
            self.analysis = None
            self.update_base_value_text()
            self.refresh_crop_display()
            messagebox.showwarning("自动分析失败", f"{error}\n\n请使用“吸管：胶片基底”点击原图中的未曝光橙色边框。")
            self.status.set("请使用胶片基底吸管；吸管始终读取原图像素。")

    def apply_pick(self: Any, x: int, y: int) -> None:
        if self.preview_source is None:
            return
        try:
            if self.pick_mode == "base":
                base = sample_median_rgb(self.preview_source, x, y, self.sample_size.get())
                self.analysis = analyze_image(
                    self.analysis_source(),
                    base=base,
                    method="eyedropper-original",
                )
                for channel, _index in BASE_CHANNELS:
                    self.base_adjust_units[channel].set(0)
                    self.base_adjust_entries[channel].set("0")
                self.status.set("已从原图像素读取胶片基底，正在刷新裁切后的预览。")
            else:
                if self.analysis is None:
                    raise ValueError("请先分析胶片基底。")
                gains = neutral_gains(
                    self.preview_source,
                    self.analysis,
                    self.controls_value(),
                    x,
                    y,
                    self.sample_size.get(),
                )
                for key, value in zip(("red_gain", "green_gain", "blue_gain"), gains):
                    self.vars[key].set(value)
                    self.entry_vars[key].set(self._format_value(key, value))
                self.status.set("中性色已按原图坐标重新计算，正在刷新预览。")
            self.pick_mode = None
            self._update_cursor()
            self._store_current_state()
            self.update_base_value_text()
            self.schedule_render(0)
        except Exception as error:
            messagebox.showerror("取样失败", str(error))

    def crop_canvas_rect(self: Any) -> tuple[float, float, float, float]:
        offset_x, offset_y, scale, width, height = self.canvas_geometry
        left, top, right, bottom = clamp_crop(self.crop_norm)
        return (
            offset_x + left * width * scale,
            offset_y + top * height * scale,
            offset_x + right * width * scale,
            offset_y + bottom * height * scale,
        )

    def draw_crop_overlay(self: Any) -> None:
        if not self.crop_editing or self.display_pil is None:
            return
        x0, y0, x1, y1 = self.crop_canvas_rect()
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#ffd35a", width=2)
        handles = {
            "nw": (x0, y0), "n": ((x0 + x1) / 2, y0), "ne": (x1, y0),
            "w": (x0, (y0 + y1) / 2), "e": (x1, (y0 + y1) / 2),
            "sw": (x0, y1), "s": ((x0 + x1) / 2, y1), "se": (x1, y1),
        }
        size = 6
        for x, y in handles.values():
            self.canvas.create_rectangle(
                x - size, y - size, x + size, y + size,
                fill="#ffd35a", outline="#222222", width=1,
            )

    def crop_hit_test(self: Any, canvas_x: float, canvas_y: float) -> str:
        x0, y0, x1, y1 = self.crop_canvas_rect()
        handles = {
            "nw": (x0, y0), "n": ((x0 + x1) / 2, y0), "ne": (x1, y0),
            "w": (x0, (y0 + y1) / 2), "e": (x1, (y0 + y1) / 2),
            "sw": (x0, y1), "s": ((x0 + x1) / 2, y1), "se": (x1, y1),
        }
        threshold = 11.0
        for name, (x, y) in handles.items():
            if abs(canvas_x - x) <= threshold and abs(canvas_y - y) <= threshold:
                return name
        if x0 <= canvas_x <= x1 and y0 <= canvas_y <= y1:
            return "move"
        return "new"

    def on_canvas_press(self: Any, event: tk.Event) -> None:
        if self.pick_mode:
            point = self.map_canvas_to_preview(event.x, event.y)
            if point is not None:
                self._apply_pick(round(point[0]), round(point[1]))
            return
        if not self.crop_editing:
            original_on_canvas_press(self, event)
            return
        if self.preview_source is None:
            return
        point = self.map_canvas_to_preview(event.x, event.y)
        if point is None:
            point = self._clamped_canvas_point(event.x, event.y)
        if point is None:
            return
        self.crop_drag_mode = self.crop_hit_test(float(event.x), float(event.y))
        self.crop_drag_start = normalized_point(point, self.preview_source.shape)
        self.crop_drag_initial = clamp_crop(self.crop_norm)
        if self.crop_drag_mode == "new":
            self.crop_norm = update_crop_from_drag(
                self.crop_drag_initial,
                "new",
                self.crop_drag_start,
                self.crop_drag_start,
            )
            self.draw_preview()

    def on_canvas_motion(self: Any, event: tk.Event) -> None:
        if not self.crop_editing or self.crop_drag_mode is None:
            original_on_canvas_motion(self, event)
            return
        if self.preview_source is None:
            return
        point = self.map_canvas_to_preview(event.x, event.y)
        if point is None:
            point = self._clamped_canvas_point(event.x, event.y)
        if point is None:
            return
        current = normalized_point(point, self.preview_source.shape)
        self.crop_norm = update_crop_from_drag(
            self.crop_drag_initial,
            self.crop_drag_mode,
            self.crop_drag_start,
            current,
        )
        self._update_crop_status()
        self.draw_preview()

    def on_canvas_release(self: Any, event: tk.Event) -> None:
        if not self.crop_editing or self.crop_drag_mode is None:
            original_on_canvas_release(self, event)
            return
        self.crop_drag_mode = None
        self._store_current_state()
        self._update_crop_status()
        self.draw_preview()

    def recalculate_for_crop(self: Any) -> None:
        if self.preview_source is None:
            return
        source = self.analysis_source()
        try:
            if self.analysis is not None and str(self.analysis.method).startswith("eyedropper"):
                self.analysis = analyze_image(
                    source,
                    base=np.asarray(self.analysis.base, dtype=np.float32),
                    method="eyedropper-original",
                )
            else:
                self.analysis = analyze_image(source, border_fraction=0.07, method="crop-border")
            self._store_current_state()
            self.update_base_value_text()
            self.schedule_render(0)
        except Exception as error:
            self.status.set(f"裁切已应用；边框分析失败：{error}")
            self.schedule_render(0)

    def toggle_crop_editing(self: Any) -> None:
        if self.preview_source is None:
            messagebox.showinfo("尚未打开图像", "请先添加并选择一张图片。")
            return
        self.crop_editing = not self.crop_editing
        self.crop_drag_mode = None
        if self.crop_editing:
            self.interaction_mode.set("crop")
            if self.crop_toggle_button is not None:
                self.crop_toggle_button.configure(text="完成裁切")
            self.refresh_crop_display()
            self.zoom_fit_view()
            self.status.set("裁切编辑：拖动八个控制点、边框中点或框内区域；也可在框外拖出新范围。")
        else:
            self.interaction_mode.set("pan")
            if self.crop_toggle_button is not None:
                self.crop_toggle_button.configure(text="裁切")
            self._store_current_state()
            self.refresh_crop_display()
            self.zoom_fit_view()
            self._update_crop_status()
            self.status.set("裁切已应用，只显示保留范围；自动分析边框将使用裁切后的区域。")
            self.recalculate_for_crop()
        self._update_cursor()

    def reset_crop(self: Any) -> None:
        self.crop_norm = FULL_CROP
        self._store_current_state()
        self.refresh_crop_display()
        self.zoom_fit_view()
        self._update_crop_status()
        self.recalculate_for_crop()

    def update_crop_status(self: Any) -> None:
        if self.crop_editing:
            left, top, right, bottom = clamp_crop(self.crop_norm)
            self.crop_status.set(f"裁切编辑：{(right - left) * 100:.0f}% × {(bottom - top) * 100:.0f}%")
        elif crop_is_full(self.crop_norm):
            self.crop_status.set("裁切：完整画面")
        else:
            left, top, right, bottom = clamp_crop(self.crop_norm)
            self.crop_status.set(f"裁切已应用：{(right - left) * 100:.0f}% × {(bottom - top) * 100:.0f}%")

    def load_index(self: Any, index: int) -> None:
        self.crop_editing = False
        self.crop_drag_mode = None
        self.interaction_mode.set("pan")
        if self.crop_toggle_button is not None:
            self.crop_toggle_button.configure(text="裁切")
        original_load_index(self, index)
        self.update_base_value_text()

    def clear_current_display(self: Any) -> None:
        self.crop_editing = False
        self.crop_drag_mode = None
        self._display_full_array = None
        self._display_view_array = None
        self._display_source_crop = FULL_CROP
        if self.crop_toggle_button is not None:
            self.crop_toggle_button.configure(text="裁切")
        original_clear_current_display(self)
        self.update_base_value_text()

    def batch_export(self: Any, indices: list[int]) -> None:
        if not indices:
            return
        if self.lr_job_data is not None:
            self._run_lr_job()
            return
        self._store_current_state()
        destination = filedialog.askdirectory(title="选择批量输出文件夹")
        if not destination:
            return
        output_dir = Path(destination)
        states = [self.items[index] for index in indices]
        raw_settings = self.raw_settings_value() if hasattr(self, "raw_settings_value") else None
        self.status.set(f"正在批量处理 {len(states)} 张照片…")

        def worker() -> None:
            try:
                for position, item in enumerate(states, start=1):
                    image, metadata = load_image(item.path, raw_settings=raw_settings)
                    source = crop_array(image, item.crop)
                    analysis_source = make_preview(source, 1800)
                    analysis = Analysis.from_dict(item.analysis) if item.analysis else analyze_image(
                        analysis_source, method="crop-border"
                    )
                    controls = Controls.from_dict(item.controls)
                    result = process_image_tiled(source, analysis, controls)
                    result = prepare_save_output(result, metadata)
                    target = output_dir / f"{item.path.stem}_PS-Sezhao.tif"
                    save_image(target, result, bit_depth=16, icc_profile=metadata.get("icc_profile"))
                    self.root.after(
                        0,
                        lambda i=position, name=item.path.name: self.status.set(
                            f"正在处理 {i}/{len(states)}：{name}"
                        ),
                    )
                self.root.after(0, lambda: self.status.set(f"批量处理完成：{output_dir}"))
            except Exception as error:
                self.root.after(0, lambda msg=str(error): messagebox.showerror("批量处理失败", msg))

        threading.Thread(target=worker, daemon=True).start()

    app_class._build_variables = build_variables
    app_class._build_preview_panel = build_preview_panel
    app_class._build_controls_panel = build_controls_panel
    app_class.controls_value = controls_value
    app_class.apply_controls = apply_controls
    app_class.on_base_scale = on_base_scale
    app_class.commit_base_entry = commit_base_entry
    app_class.adjust_base = adjust_base
    app_class.reset_base_adjust = reset_base_adjust
    app_class.base_adjust_changed = base_adjust_changed
    app_class.update_base_value_text = update_base_value_text
    app_class._set_display_image = set_display_image
    app_class.refresh_crop_display = refresh_crop_display
    app_class.map_canvas_to_preview = map_canvas_to_preview
    app_class.analysis_source = analysis_source
    app_class.auto_analyze = auto_analyze
    app_class._apply_pick = apply_pick
    app_class._draw_crop_overlay = draw_crop_overlay
    app_class.crop_canvas_rect = crop_canvas_rect
    app_class.crop_hit_test = crop_hit_test
    app_class.on_canvas_press = on_canvas_press
    app_class.on_canvas_motion = on_canvas_motion
    app_class.on_canvas_release = on_canvas_release
    app_class.recalculate_for_crop = recalculate_for_crop
    app_class.toggle_crop_editing = toggle_crop_editing
    app_class.reset_crop = reset_crop
    app_class._update_crop_status = update_crop_status
    app_class.load_index = load_index
    app_class._clear_current_display = clear_current_display
    app_class._batch_export = batch_export
    app_class._v052_source_crop_patch_applied = True

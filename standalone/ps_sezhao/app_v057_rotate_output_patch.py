from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import threading
from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .engine import Analysis, Controls, analyze_image
from .io_utils import load_image, make_preview, save_image
from .processing import process_image_tiled
from .raw_io import prepare_save_output
from .workspace import (
    clamp_crop,
    crop_array,
    normalize_rotation,
    rotate_array,
    rotate_crop,
)

OUTPUT_FORMATS: dict[str, tuple[str, int, str]] = {
    "16 位 TIFF（无损）": (".tif", 16, "16 位 TIFF"),
    "JPEG": (".jpg", 8, "JPEG"),
    "PNG（无损）": (".png", 8, "PNG"),
}


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def apply_v057_rotate_output_patch(app_class: Type[Any]) -> None:
    """Add per-photo rotation, a fixed output panel and selectable save quality."""

    if getattr(app_class, "_v057_rotate_output_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_preview_panel = app_class._build_preview_panel
    original_build_controls_panel = app_class._build_controls_panel
    original_load_index = app_class.load_index
    original_clear_current_display = app_class._clear_current_display
    original_show_raw_loading_preview = getattr(app_class, "_show_raw_loading_preview", None)
    original_accept_raw_decode = getattr(app_class, "_accept_raw_decode", None)
    original_item_snapshot = getattr(app_class, "item_snapshot", None)
    original_restore_snapshot = getattr(app_class, "restore_snapshot", None)
    original_run_lr_job = getattr(app_class, "_run_lr_job", None)

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.output_format_label = tk.StringVar(value="16 位 TIFF（无损）")
        self.jpeg_quality = tk.IntVar(value=95)
        self.rotation_status = tk.StringVar(value="旋转：0°")
        self.jpeg_quality_spinbox: ttk.Spinbox | None = None

    def build_preview_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_preview_panel(self, parent)
        viewbar = next((child for child in parent.winfo_children() if isinstance(child, ttk.Frame)), None)
        if viewbar is None:
            return

        crop_label = None
        for child in viewbar.winfo_children():
            if isinstance(child, ttk.Label):
                try:
                    if str(child.cget("textvariable")) == str(self.crop_status):
                        crop_label = child
                        break
                except tk.TclError:
                    continue

        viewbar.columnconfigure(12, weight=0)
        viewbar.columnconfigure(15, weight=1)
        ttk.Separator(viewbar, orient="vertical").grid(row=0, column=11, sticky="ns", padx=5)
        ttk.Button(
            viewbar,
            text="左转 90°",
            command=lambda: self.rotate_current(-90),
        ).grid(row=0, column=12, padx=2)
        ttk.Button(
            viewbar,
            text="右转 90°",
            command=lambda: self.rotate_current(90),
        ).grid(row=0, column=13, padx=2)
        ttk.Label(viewbar, textvariable=self.rotation_status).grid(row=0, column=14, padx=(5, 3))
        if crop_label is not None:
            crop_label.grid_configure(row=0, column=16, sticky="e")

    def build_controls_panel(self: Any, parent: ttk.Frame) -> None:
        fixed = ttk.LabelFrame(parent, text="输出（固定）", padding=7)
        fixed.pack(side="top", fill="x", pady=(0, 6))
        fixed.columnconfigure((0, 1), weight=1)

        settings = ttk.Frame(fixed)
        settings.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="格式").grid(row=0, column=0, sticky="w", padx=(0, 5))
        format_box = ttk.Combobox(
            settings,
            textvariable=self.output_format_label,
            values=tuple(OUTPUT_FORMATS.keys()),
            state="readonly",
            width=19,
        )
        format_box.grid(row=0, column=1, sticky="ew")
        format_box.bind("<<ComboboxSelected>>", lambda _event: self._update_output_quality_state())
        ttk.Label(settings, text="JPEG 质量").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        self.jpeg_quality_spinbox = ttk.Spinbox(
            settings,
            from_=1,
            to=100,
            increment=1,
            textvariable=self.jpeg_quality,
            width=7,
            justify="right",
        )
        self.jpeg_quality_spinbox.grid(row=1, column=1, sticky="w", pady=(5, 0))

        ttk.Button(fixed, text="保存当前", command=self.save_current).grid(
            row=1, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(fixed, text="导出选中", command=self.export_selected).grid(
            row=1, column=1, sticky="ew", padx=(3, 0)
        )
        ttk.Button(fixed, text="导出全部", command=self.export_all).grid(
            row=2, column=0, sticky="ew", padx=(0, 3), pady=(4, 0)
        )
        ttk.Button(fixed, text="LR 批量应用并完成", command=self.apply_all).grid(
            row=2, column=1, sticky="ew", padx=(3, 0), pady=(4, 0)
        )

        scroll_host = ttk.Frame(parent)
        scroll_host.pack(side="top", fill="both", expand=True)
        original_build_controls_panel(self, scroll_host)

        # These were duplicated in the left file panel. Keep the left-side
        # buttons, remove the repeated right-side sync block and old output block.
        for widget in _walk_widgets(self.controls):
            if not isinstance(widget, ttk.LabelFrame):
                continue
            try:
                title = str(widget.cget("text"))
            except tk.TclError:
                continue
            if title in {"多图同步", "输出"}:
                widget.grid_remove()

        self._update_output_quality_state()

    def update_output_quality_state(self: Any) -> None:
        if self.jpeg_quality_spinbox is None:
            return
        state = "normal" if self.output_format_label.get() == "JPEG" else "disabled"
        self.jpeg_quality_spinbox.configure(state=state)

    def output_spec(self: Any) -> tuple[str, int, str]:
        return OUTPUT_FORMATS.get(self.output_format_label.get(), OUTPUT_FORMATS["16 位 TIFF（无损）"])

    def output_quality(self: Any) -> int:
        try:
            quality = int(self.jpeg_quality.get())
        except (TypeError, ValueError, tk.TclError):
            quality = 95
        quality = min(100, max(1, quality))
        self.jpeg_quality.set(quality)
        return quality

    def invalidate_render(self: Any) -> None:
        self.render_generation += 1
        if self.render_after:
            try:
                self.root.after_cancel(self.render_after)
            except tk.TclError:
                pass
            self.render_after = None

    def rotate_loaded_buffers(self: Any, clockwise_degrees: int) -> None:
        rotation = normalize_rotation(clockwise_degrees)
        if rotation == 0:
            return
        self._invalidate_render()
        if self.full_image is not None:
            self.full_image = rotate_array(self.full_image, rotation)
        if self.preview_source is not None:
            self.preview_source = rotate_array(self.preview_source, rotation)
        if self.preview_result is not None:
            self.preview_result = rotate_array(self.preview_result, rotation)

    def refresh_after_rotation(self: Any) -> None:
        shown = self.preview_result if self.preview_result is not None else self.preview_source
        if shown is not None:
            self._set_display_image(shown)
            self.zoom_fit_view()
        self._update_crop_status()
        if self.current_index is not None:
            self._update_tree_row(self.current_index)
        item = self.current_item()
        self.rotation_status.set(f"旋转：{item.rotation if item is not None else 0}°")

    def load_index(self: Any, index: int) -> None:
        original_load_index(self, index)
        item = self.current_item()
        if item is None or self.current_index != index:
            return
        self.rotation_status.set(f"旋转：{item.rotation}°")

        # RAW decoding completes asynchronously and is rotated in
        # _accept_raw_decode. Ordinary images are already loaded here.
        if self.full_image is None or normalize_rotation(item.rotation) == 0:
            return
        self._rotate_loaded_buffers(item.rotation)
        self._refresh_after_rotation()
        self.schedule_render(0)

    def clear_current_display(self: Any) -> None:
        original_clear_current_display(self)
        self.rotation_status.set("旋转：0°")

    def show_raw_loading_preview(
        self: Any,
        generation: int,
        index: int,
        preview: Any,
        metadata: dict[str, Any],
    ) -> None:
        if original_show_raw_loading_preview is None:
            return
        rotation = self.items[index].rotation if 0 <= index < len(self.items) else 0
        original_show_raw_loading_preview(
            self,
            generation,
            index,
            rotate_array(preview, rotation),
            metadata,
        )

    def accept_raw_decode(
        self: Any,
        generation: int,
        index: int,
        image: Any,
        metadata: dict[str, Any],
    ) -> None:
        if original_accept_raw_decode is None:
            return
        rotation = self.items[index].rotation if 0 <= index < len(self.items) else 0
        original_accept_raw_decode(
            self,
            generation,
            index,
            rotate_array(image, rotation),
            metadata,
        )
        if generation == self.raw_decode_generation and index == self.current_index:
            self.rotation_status.set(f"旋转：{normalize_rotation(rotation)}°")

    def rotate_current(self: Any, clockwise_degrees: int) -> None:
        item = self.current_item()
        if item is None or self.preview_source is None:
            messagebox.showinfo("尚未打开图像", "请等待当前图片读取完成后再旋转。")
            return

        delta = normalize_rotation(clockwise_degrees)
        if delta == 0:
            return

        # Finish crop editing before rotating. The crop rectangle itself is
        # transformed so it continues to cover the same physical image area.
        self.crop_editing = False
        self.crop_drag_mode = None
        self.interaction_mode.set("pan")
        if getattr(self, "crop_toggle_button", None) is not None:
            self.crop_toggle_button.configure(text="裁切")

        item.rotation = normalize_rotation(item.rotation + delta)
        item.crop = rotate_crop(item.crop, delta)
        self.crop_norm = item.crop
        self._rotate_loaded_buffers(delta)
        self._store_current_state()
        self._refresh_after_rotation()
        self.status.set(f"已旋转到 {item.rotation}°；预览、裁切和导出将使用此方向。")
        if hasattr(self, "_record_history"):
            self._record_history(force=True, kind="rotation")
        self.schedule_render(0)

    def item_snapshot(self: Any, index: int | None = None) -> dict[str, Any] | None:
        if original_item_snapshot is None:
            return None
        snapshot = original_item_snapshot(self, index)
        if snapshot is None:
            return None
        target = self.current_index if index is None else index
        if target is not None and 0 <= target < len(self.items):
            snapshot["rotation"] = int(self.items[target].rotation)
        return snapshot

    def restore_snapshot(self: Any, snapshot: dict[str, Any]) -> None:
        if original_restore_snapshot is None:
            return
        item = self.current_item()
        if item is None:
            return
        target_rotation = normalize_rotation(snapshot.get("rotation", item.rotation))
        delta = normalize_rotation(target_rotation - item.rotation)
        if delta:
            item.rotation = target_rotation
            self._rotate_loaded_buffers(delta)
        original_restore_snapshot(self, snapshot)
        self._refresh_after_rotation()

    def save_current(self: Any) -> None:
        if self.full_image is None or self.analysis is None or self.current_item() is None:
            return
        self._store_current_state()
        item = self.current_item()
        assert item is not None
        extension, _bit_depth, format_name = self._output_spec()
        default_name = item.path.stem + "_PS-Sezhao" + extension
        target = filedialog.asksaveasfilename(
            title="保存正片",
            initialfile=default_name,
            defaultextension=extension,
            filetypes=[(format_name, "*" + extension), ("全部文件", "*.*")],
        )
        if not target:
            return
        self._process_and_save(
            self.full_image,
            Path(target),
            self.analysis,
            self.controls_value(),
            self.crop_norm,
            self.metadata,
        )

    def process_and_save(
        self: Any,
        image: Any,
        target: Path,
        analysis: Analysis,
        controls: Controls,
        crop: tuple[float, float, float, float],
        metadata: dict[str, Any],
    ) -> None:
        self.status.set(f"正在生成 {target.name}…")
        quality = self._output_quality()
        _extension, bit_depth, _format_name = self._output_spec()

        def worker() -> None:
            try:
                source = crop_array(image, crop)
                result = process_image_tiled(source, analysis, controls)
                result = prepare_save_output(result, metadata)
                save_image(
                    target,
                    result,
                    bit_depth=bit_depth,
                    icc_profile=metadata.get("icc_profile"),
                    jpeg_quality=quality,
                )
                self.root.after(0, lambda: self.status.set(f"已保存：{target}"))
            except Exception as error:
                self.root.after(
                    0,
                    lambda message=str(error): messagebox.showerror("保存失败", message),
                )

        threading.Thread(target=worker, daemon=True).start()

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
        extension, bit_depth, _format_name = self._output_spec()
        quality = self._output_quality()
        self.status.set(f"正在批量处理 {len(states)} 张照片…")

        def worker() -> None:
            try:
                for position, item in enumerate(states, start=1):
                    image, metadata = load_image(item.path, raw_settings=raw_settings)
                    image = rotate_array(image, item.rotation)
                    source = crop_array(image, item.crop)
                    analysis_source = make_preview(source, 1800)
                    analysis = Analysis.from_dict(item.analysis) if item.analysis else analyze_image(
                        analysis_source,
                        method="crop-border",
                    )
                    controls = Controls.from_dict(item.controls)
                    result = process_image_tiled(source, analysis, controls)
                    result = prepare_save_output(result, metadata)
                    target = output_dir / f"{item.path.stem}_PS-Sezhao{extension}"
                    save_image(
                        target,
                        result,
                        bit_depth=bit_depth,
                        icc_profile=metadata.get("icc_profile"),
                        jpeg_quality=quality,
                    )
                    self.root.after(
                        0,
                        lambda i=position, name=item.path.name: self.status.set(
                            f"正在处理 {i}/{len(states)}：{name}"
                        ),
                    )
                self.root.after(0, lambda: self.status.set(f"批量处理完成：{output_dir}"))
            except Exception as error:
                self.root.after(
                    0,
                    lambda message=str(error): messagebox.showerror("批量处理失败", message),
                )

        threading.Thread(target=worker, daemon=True).start()

    def run_lr_job(self: Any) -> None:
        if original_run_lr_job is None:
            return
        if self.lr_job_data is not None:
            job_items = self.lr_job_data.get("items") or []
            for index, job_item in enumerate(job_items):
                if index >= len(self.items):
                    break
                job_item["rotation"] = int(self.items[index].rotation)
            self.lr_job_data["jpeg_quality"] = self._output_quality()
        original_run_lr_job(self)

    app_class._build_variables = build_variables
    app_class._build_preview_panel = build_preview_panel
    app_class._build_controls_panel = build_controls_panel
    app_class._update_output_quality_state = update_output_quality_state
    app_class._output_spec = output_spec
    app_class._output_quality = output_quality
    app_class._invalidate_render = invalidate_render
    app_class._rotate_loaded_buffers = rotate_loaded_buffers
    app_class._refresh_after_rotation = refresh_after_rotation
    app_class.load_index = load_index
    app_class._clear_current_display = clear_current_display
    if original_show_raw_loading_preview is not None:
        app_class._show_raw_loading_preview = show_raw_loading_preview
    if original_accept_raw_decode is not None:
        app_class._accept_raw_decode = accept_raw_decode
    app_class.rotate_current = rotate_current
    if original_item_snapshot is not None:
        app_class.item_snapshot = item_snapshot
        app_class._item_snapshot = item_snapshot
    if original_restore_snapshot is not None:
        app_class.restore_snapshot = restore_snapshot
        app_class._restore_snapshot = restore_snapshot
    app_class.save_current = save_current
    app_class._process_and_save = process_and_save
    app_class._batch_export = batch_export
    if original_run_lr_job is not None:
        app_class._run_lr_job = run_lr_job
    app_class._v057_rotate_output_applied = True

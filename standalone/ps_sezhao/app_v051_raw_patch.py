from __future__ import annotations

from pathlib import Path
import threading
import traceback
from typing import Any, Type

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .engine import Analysis, Controls, analyze_image
from .io_utils import load_image, make_preview, save_image
from .processing import process_image_tiled
from .raw_io import (
    RAW_EXTENSIONS,
    RawDecodeSettings,
    extract_raw_preview,
    is_raw_path,
    prepare_display_output,
    prepare_save_output,
    raw_runtime_summary,
)
from .workspace import PhotoState, SUPPORTED_EXTENSIONS, clamp_crop, crop_array

WB_LABELS = {
    "相机拍摄白平衡": "camera",
    "日光白平衡": "daylight",
    "自动白平衡": "auto",
    "自定义通道倍率": "custom",
}
HIGHLIGHT_LABELS = {
    "混合高光（推荐）": "blend",
    "直接裁切": "clip",
    "重建高光": "reconstruct",
}
DEMOSAIC_LABELS = {
    "AHD 标准质量": "ahd",
    "线性快速": "linear",
    "VNG": "vng",
    "PPG": "ppg",
}


def apply_raw_patch(app_class: Type[Any]) -> None:
    """Add v0.5.1 camera RAW loading without rewriting the v0.5.0 UI."""

    if getattr(app_class, "_v051_raw_patch_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_controls_panel = app_class._build_controls_panel
    original_load_index = app_class.load_index
    original_clear_current_display = app_class._clear_current_display

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.raw_wb_label = tk.StringVar(value="相机拍摄白平衡")
        self.raw_highlight_label = tk.StringVar(value="混合高光（推荐）")
        self.raw_demosaic_label = tk.StringVar(value="AHD 标准质量")
        self.raw_use_embedded_preview = tk.BooleanVar(value=True)
        self.raw_half_size_preview = tk.BooleanVar(value=True)
        self.raw_custom_wb_vars = [tk.StringVar(value="1.000") for _ in range(4)]
        self.raw_info = tk.StringVar(value=raw_runtime_summary())
        self.raw_decode_generation = 0
        self.raw_custom_entries: list[ttk.Entry] = []

    def build_controls_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_controls_panel(self, parent)
        row = self.controls.grid_size()[1]
        frame = ttk.LabelFrame(self.controls, text="相机 RAW 解码 · v0.5.1", padding=7)
        frame.grid(row=row, column=0, sticky="ew", pady=(2, 12))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="白平衡").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        wb = ttk.Combobox(
            frame,
            textvariable=self.raw_wb_label,
            values=tuple(WB_LABELS.keys()),
            state="readonly",
            width=20,
        )
        wb.grid(row=0, column=1, sticky="ew", pady=2)
        wb.bind("<<ComboboxSelected>>", lambda _event: self._update_custom_wb_state())

        ttk.Label(frame, text="高光处理").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Combobox(
            frame,
            textvariable=self.raw_highlight_label,
            values=tuple(HIGHLIGHT_LABELS.keys()),
            state="readonly",
            width=20,
        ).grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="去马赛克").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Combobox(
            frame,
            textvariable=self.raw_demosaic_label,
            values=tuple(DEMOSAIC_LABELS.keys()),
            state="readonly",
            width=20,
        ).grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(frame, text="自定义 WB").grid(row=3, column=0, sticky="nw", padx=(0, 5), pady=(4, 2))
        custom = ttk.Frame(frame)
        custom.grid(row=3, column=1, sticky="ew", pady=(4, 2))
        for index, label in enumerate(("R", "G", "B", "G2")):
            ttk.Label(custom, text=label).grid(row=0, column=index * 2, padx=(0 if index == 0 else 5, 2))
            entry = ttk.Entry(custom, textvariable=self.raw_custom_wb_vars[index], width=6, justify="right")
            entry.grid(row=0, column=index * 2 + 1)
            self.raw_custom_entries.append(entry)

        ttk.Checkbutton(
            frame,
            text="优先读取 RAW 内嵌预览",
            variable=self.raw_use_embedded_preview,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(
            frame,
            text="无内嵌预览时使用半尺寸快速预览",
            variable=self.raw_half_size_preview,
        ).grid(row=5, column=0, columnspan=2, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(6, 3))
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text="重新解码当前 RAW", command=self.reload_current_raw).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(buttons, text="恢复 RAW 默认", command=self.reset_raw_settings).grid(
            row=0, column=1, sticky="ew", padx=(3, 0)
        )

        ttk.Label(
            frame,
            text="固定流程：16 位线性解码 · ProPhoto RGB · 关闭自动提亮；导出 TIFF 自动嵌入 ProPhoto ICC。",
            foreground="#666",
            wraplength=295,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 2))
        ttk.Label(frame, textvariable=self.raw_info, foreground="#666", wraplength=295).grid(
            row=8, column=0, columnspan=2, sticky="w"
        )
        self._update_custom_wb_state()

    def raw_settings_value(self: Any) -> RawDecodeSettings:
        custom: list[float] = []
        for variable in self.raw_custom_wb_vars:
            try:
                custom.append(float(variable.get().strip()))
            except (TypeError, ValueError):
                custom.append(1.0)
        settings = RawDecodeSettings(
            wb_mode=WB_LABELS.get(self.raw_wb_label.get(), "camera"),
            custom_wb=tuple(custom),
            highlight_mode=HIGHLIGHT_LABELS.get(self.raw_highlight_label.get(), "blend"),
            demosaic=DEMOSAIC_LABELS.get(self.raw_demosaic_label.get(), "ahd"),
            use_embedded_preview=self.raw_use_embedded_preview.get(),
            half_size_preview=self.raw_half_size_preview.get(),
        ).sanitized()
        for variable, value in zip(self.raw_custom_wb_vars, settings.custom_wb):
            variable.set(f"{value:.3f}")
        return settings

    def update_custom_wb_state(self: Any) -> None:
        state = "normal" if WB_LABELS.get(self.raw_wb_label.get()) == "custom" else "disabled"
        for entry in self.raw_custom_entries:
            entry.configure(state=state)

    def reset_raw_settings(self: Any) -> None:
        self.raw_wb_label.set("相机拍摄白平衡")
        self.raw_highlight_label.set("混合高光（推荐）")
        self.raw_demosaic_label.set("AHD 标准质量")
        self.raw_use_embedded_preview.set(True)
        self.raw_half_size_preview.set(True)
        for variable in self.raw_custom_wb_vars:
            variable.set("1.000")
        self._update_custom_wb_state()
        self.raw_info.set(raw_runtime_summary())

    def reload_current_raw(self: Any) -> None:
        item = self.current_item()
        if item is None or not is_raw_path(item.path):
            messagebox.showinfo("当前不是 RAW", "请先在左侧选择一张相机 RAW 文件。")
            return
        item.analysis = None
        self.analysis = None
        self.load_index(self.current_index)

    def open_dialog(self: Any) -> None:
        raw_patterns = " ".join(f"*{extension}" for extension in sorted(RAW_EXTENSIONS))
        paths = filedialog.askopenfilenames(
            title="添加扫描、翻拍负片或相机 RAW",
            filetypes=[
                ("支持的图像与 RAW", "*.tif *.tiff *.jpg *.jpeg *.png *.bmp *.webp " + raw_patterns),
                ("相机 RAW", raw_patterns),
                ("TIFF / 常规图像", "*.tif *.tiff *.jpg *.jpeg *.png *.bmp *.webp"),
                ("全部文件", "*.*"),
            ],
        )
        if paths:
            self.open_paths([Path(path) for path in paths])

    def open_paths(self: Any, paths: list[Path], *, replace: bool = False) -> None:
        valid = [Path(path) for path in paths if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS]
        rejected = len(paths) - len(valid)
        if not valid:
            if rejected:
                messagebox.showwarning("没有支持的文件", "所选文件不是可识别的图像或相机 RAW。")
            return
        if replace:
            self.items.clear()
            self.current_index = None
        self._store_current_state()
        existing = {str(item.path.resolve()) for item in self.items}
        base_controls = self.controls_value().to_dict()
        new_indices: list[int] = []
        for path in valid:
            resolved = str(path.resolve())
            if resolved in existing:
                continue
            self.items.append(PhotoState(path=path, controls=dict(base_controls)))
            existing.add(resolved)
            new_indices.append(len(self.items) - 1)
        self.refresh_file_tree()
        if new_indices:
            self.load_index(new_indices[0])
            self.file_tree.selection_set([str(index) for index in new_indices])
            self.file_tree.focus(str(new_indices[0]))
        if rejected:
            self.status.set(f"已添加 {len(new_indices)} 张；忽略 {rejected} 个不支持的文件。")

    def load_index(self: Any, index: int) -> None:
        if index < 0 or index >= len(self.items):
            return
        item = self.items[index]
        if not is_raw_path(item.path):
            original_load_index(self, index)
            return

        self._store_current_state()
        self.raw_decode_generation += 1
        generation = self.raw_decode_generation
        settings = self.raw_settings_value()
        self.current_index = index
        self.full_image = None
        self.preview_source = None
        self.preview_result = None
        self.metadata = {}
        self.crop_norm = clamp_crop(item.crop)
        self.analysis = Analysis.from_dict(item.analysis) if item.analysis else None
        self.apply_controls(Controls.from_dict(item.controls))
        self.canvas.delete("all")
        self.status.set(f"正在读取 RAW 内嵌预览：{item.path.name}…")
        self.raw_info.set(f"{raw_runtime_summary()} · 正在解码")

        self._tree_updating = True
        try:
            self.file_tree.selection_add(str(index))
            self.file_tree.focus(str(index))
            self.file_tree.see(str(index))
        finally:
            self._tree_updating = False
        self._update_crop_status()

        def worker() -> None:
            try:
                try:
                    preview, preview_metadata = extract_raw_preview(item.path, settings, max_edge=1800)
                    self.root.after(
                        0,
                        lambda p=preview, m=preview_metadata: self._show_raw_loading_preview(
                            generation, index, p, m
                        ),
                    )
                except Exception:
                    # Full decoding below gives the authoritative and clearer error.
                    pass
                image, metadata = load_image(item.path, raw_settings=settings)
                self.root.after(
                    0,
                    lambda img=image, meta=metadata: self._accept_raw_decode(
                        generation, index, img, meta
                    ),
                )
            except Exception as error:
                message = str(error)
                self.root.after(0, lambda msg=message: self._raw_decode_error(generation, index, msg))

        threading.Thread(target=worker, daemon=True).start()

    def show_raw_loading_preview(
        self: Any,
        generation: int,
        index: int,
        preview: Any,
        metadata: dict[str, Any],
    ) -> None:
        if generation != self.raw_decode_generation or index != self.current_index:
            return
        self._set_display_image(preview)
        source = metadata.get("preview_source", "embedded")
        source_label = "内嵌预览" if source == "embedded" else "快速解码预览"
        self.status.set(f"已显示 {source_label}；正在进行 16 位线性 RAW 解码…")

    def accept_raw_decode(
        self: Any,
        generation: int,
        index: int,
        image: Any,
        metadata: dict[str, Any],
    ) -> None:
        if generation != self.raw_decode_generation or index != self.current_index:
            return
        item = self.items[index]
        self.full_image = image
        self.preview_source = make_preview(image, 1800)
        self.preview_result = None
        self.metadata = metadata
        self.crop_norm = clamp_crop(item.crop)
        self.analysis = Analysis.from_dict(item.analysis) if item.analysis else None
        self._set_display_image(prepare_display_output(self.preview_source, metadata))
        self.zoom_fit_view()
        self._update_crop_status()
        size = metadata.get("raw_size") or {}
        dimensions = f"{size.get('width', image.shape[1])}×{size.get('height', image.shape[0])}"
        self.raw_info.set(
            f"{metadata.get('raw_runtime', raw_runtime_summary())} · {dimensions} · 16 位线性 ProPhoto"
        )
        if self.analysis is None:
            self.auto_analyze()
        else:
            self.status.set(f"RAW 解码完成：{item.path.name}")
            self.schedule_render(0)

    def raw_decode_error(self: Any, generation: int, index: int, message: str) -> None:
        if generation != self.raw_decode_generation or index != self.current_index:
            return
        self.status.set("RAW 解码失败。")
        self.raw_info.set(raw_runtime_summary())
        messagebox.showerror("无法打开相机 RAW", message)

    def clear_current_display(self: Any) -> None:
        self.raw_decode_generation += 1
        original_clear_current_display(self)

    def render_preview(self: Any) -> None:
        self.render_after = None
        if self.analysis is None or self.preview_source is None:
            return
        self.render_generation += 1
        generation = self.render_generation
        controls = self.controls_value()
        analysis = self.analysis
        source = self.preview_source.copy()
        metadata = dict(self.metadata)
        self.status.set("正在更新大图预览…")

        def worker() -> None:
            try:
                result = process_image_tiled(source, analysis, controls)
                display = prepare_display_output(result, metadata)
                self.root.after(0, lambda: self._accept_render(generation, display))
            except Exception as error:
                trace = traceback.format_exc()
                self.root.after(0, lambda err=error, tr=trace: self._render_error(err, tr))

        threading.Thread(target=worker, daemon=True).start()

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

        def worker() -> None:
            try:
                source = crop_array(image, crop)
                result = process_image_tiled(source, analysis, controls)
                result = prepare_save_output(result, metadata)
                save_image(target, result, bit_depth=16, icc_profile=metadata.get("icc_profile"))
                self.root.after(0, lambda: self.status.set(f"已保存：{target}"))
            except Exception as error:
                message = str(error)
                self.root.after(0, lambda msg=message: messagebox.showerror("保存失败", msg))

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
        raw_settings = self.raw_settings_value()
        self.status.set(f"正在批量处理 {len(states)} 张照片…")

        def worker() -> None:
            try:
                for position, item in enumerate(states, start=1):
                    image, metadata = load_image(item.path, raw_settings=raw_settings)
                    analysis_source = make_preview(image, 1800)
                    analysis = Analysis.from_dict(item.analysis) if item.analysis else analyze_image(analysis_source)
                    controls = Controls.from_dict(item.controls)
                    source = crop_array(image, item.crop)
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
                message = str(error)
                self.root.after(0, lambda msg=message: messagebox.showerror("批量处理失败", msg))

        threading.Thread(target=worker, daemon=True).start()

    app_class._build_variables = build_variables
    app_class._build_controls_panel = build_controls_panel
    app_class.raw_settings_value = raw_settings_value
    app_class._update_custom_wb_state = update_custom_wb_state
    app_class.reset_raw_settings = reset_raw_settings
    app_class.reload_current_raw = reload_current_raw
    app_class.open_dialog = open_dialog
    app_class.open_paths = open_paths
    app_class.load_index = load_index
    app_class._show_raw_loading_preview = show_raw_loading_preview
    app_class._accept_raw_decode = accept_raw_decode
    app_class._raw_decode_error = raw_decode_error
    app_class._clear_current_display = clear_current_display
    app_class.render_preview = render_preview
    app_class._process_and_save = process_and_save
    app_class._batch_export = batch_export
    app_class._v051_raw_patch_applied = True

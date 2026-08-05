from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
import threading
from typing import Any, Iterator, Mapping, Type
import uuid

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..core.geometry import GeometrySettings, apply_photo_geometry
from ..core.output import (
    FORMAT_SPECS,
    ContactSheetEntry,
    OutputSettings,
    build_contact_sheet,
    output_metadata,
    prepare_output,
    render_filename,
    resolve_destination,
    save_output_file,
    settings_for_contact_sheet,
)
from ..engine import Analysis, Controls, analyze_image
from ..io_utils import load_image, make_preview
from ..processing import ProcessingCancelled, process_image_tiled
from ..raw_io import RawDecodeSettings, prepare_save_output
from ..workspace import crop_array, rotate_array
from .output_service import ExportTask, OutputQueueService


COLOR_SPACE_LABELS = {
    "保留输入 ICC": "preserve",
    "ProPhoto RGB（高保真）": "prophoto",
    "sRGB（网页/手机）": "srgb",
}
RESIZE_MODE_LABELS = {
    "原始尺寸": "original",
    "限制最长边": "long_edge",
    "固定宽度": "width",
    "固定高度": "height",
    "百分比": "percent",
}
RESAMPLE_LABELS = {
    "Lanczos（高质量）": "lanczos",
    "双三次": "bicubic",
    "双线性": "bilinear",
    "最近邻": "nearest",
}
SHARPEN_LABELS = {
    "关闭": "off",
    "轻微": "low",
    "标准": "standard",
    "较强": "high",
}
COLLISION_LABELS = {
    "自动编号": "auto_number",
    "覆盖已有文件": "overwrite",
    "跳过已有文件": "skip",
    "遇到重名时报错": "error",
}
CONTACT_BACKGROUND_LABELS = {"深色": "dark", "浅色": "light"}


def _inverse(mapping: Mapping[str, str], value: str, default: str) -> str:
    for label, key in mapping.items():
        if key == value:
            return label
    return default


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


@dataclass(frozen=True)
class CompleteExportTask(ExportTask):
    output_settings: OutputSettings | Mapping[str, Any] | None = None

    def normalized(self) -> "CompleteExportTask":
        base = super().normalized()
        settings = (
            self.output_settings
            if isinstance(self.output_settings, OutputSettings)
            else OutputSettings.from_dict(self.output_settings)
        ).sanitized()
        return CompleteExportTask(
            source=base.source,
            destination=base.destination,
            controls=base.controls,
            crop=base.crop,
            rotation=base.rotation,
            geometry=base.geometry,
            analysis=base.analysis,
            raw_settings=base.raw_settings,
            bit_depth=settings.bit_depth,
            jpeg_quality=settings.jpeg_quality,
            label=base.label,
            output_settings=settings,
        )


def apply_complete_output_pipeline(app_class: Type[Any]) -> None:
    """Add complete per-photo output controls and patch the queue finalization stage."""

    if getattr(app_class, "_complete_output_pipeline_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_controls_panel = app_class._build_controls_panel
    original_store_current_state = app_class._store_current_state
    original_load_index = app_class.load_index

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.output_color_space_label = tk.StringVar(value="ProPhoto RGB（高保真）")
        self.output_resize_mode_label = tk.StringVar(value="原始尺寸")
        self.output_resize_value = tk.DoubleVar(value=3000.0)
        self.output_allow_upscale = tk.BooleanVar(value=False)
        self.output_resample_label = tk.StringVar(value="Lanczos（高质量）")
        self.output_sharpen_label = tk.StringVar(value="关闭")
        self.output_filename_template = tk.StringVar(value="{stem}_PS-Sezhao")
        self.output_collision_label = tk.StringVar(value="自动编号")
        self.output_embed_metadata = tk.BooleanVar(value=True)
        self.output_roll_name = tk.StringVar(value="")
        self.output_film_stock = tk.StringVar(value="")
        self.output_camera = tk.StringVar(value="")
        self.output_capture_date = tk.StringVar(value="")
        self.output_frame_number = tk.StringVar(value="")
        self.output_note = tk.StringVar(value="")
        self.contact_columns = tk.IntVar(value=5)
        self.contact_cell_size = tk.IntVar(value=360)
        self.contact_labels = tk.BooleanVar(value=True)
        self.contact_background_label = tk.StringVar(value="深色")
        self.output_settings_button: ttk.Button | None = None
        self.contact_sheet_button: ttk.Button | None = None
        self._contact_sheet_running = False

    def build_controls_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_controls_panel(self, parent)
        fixed = next(
            (
                child
                for child in parent.winfo_children()
                if isinstance(child, ttk.LabelFrame)
                and str(child.cget("text")) == "输出（固定）"
            ),
            None,
        )
        if fixed is None:
            return
        settings_frame = None
        format_box = None
        for widget in _walk_widgets(fixed):
            if isinstance(widget, ttk.Combobox):
                try:
                    if str(widget.cget("textvariable")) == str(self.output_format_label):
                        format_box = widget
                        settings_frame = widget.master
                        break
                except tk.TclError:
                    continue
        if format_box is not None:
            format_box.configure(values=tuple(FORMAT_SPECS.keys()))
        if settings_frame is None:
            return
        settings_frame.columnconfigure((0, 1), weight=1)
        self.output_settings_button = ttk.Button(
            settings_frame,
            text="详细输出设置…",
            command=self.open_output_settings_dialog,
        )
        self.output_settings_button.grid(row=2, column=0, sticky="ew", padx=(0, 3), pady=(7, 0))
        self.contact_sheet_button = ttk.Button(
            settings_frame,
            text="生成接触印样…",
            command=self.generate_contact_sheet,
        )
        self.contact_sheet_button.grid(row=2, column=1, sticky="ew", padx=(3, 0), pady=(7, 0))

    def collect_output_settings(self: Any) -> OutputSettings:
        return OutputSettings(
            format_label=self.output_format_label.get(),
            jpeg_quality=self._output_quality(),
            color_space=COLOR_SPACE_LABELS.get(self.output_color_space_label.get(), "prophoto"),
            resize_mode=RESIZE_MODE_LABELS.get(self.output_resize_mode_label.get(), "original"),
            resize_value=self.output_resize_value.get(),
            allow_upscale=self.output_allow_upscale.get(),
            resample=RESAMPLE_LABELS.get(self.output_resample_label.get(), "lanczos"),
            sharpen=SHARPEN_LABELS.get(self.output_sharpen_label.get(), "off"),
            filename_template=self.output_filename_template.get(),
            collision_policy=COLLISION_LABELS.get(self.output_collision_label.get(), "auto_number"),
            embed_metadata=self.output_embed_metadata.get(),
            roll_name=self.output_roll_name.get(),
            film_stock=self.output_film_stock.get(),
            camera=self.output_camera.get(),
            capture_date=self.output_capture_date.get(),
            frame_number=self.output_frame_number.get(),
            note=self.output_note.get(),
            contact_columns=self.contact_columns.get(),
            contact_cell_size=self.contact_cell_size.get(),
            contact_labels=self.contact_labels.get(),
            contact_background=CONTACT_BACKGROUND_LABELS.get(self.contact_background_label.get(), "dark"),
        ).sanitized()

    def apply_output_settings_to_ui(
        self: Any,
        settings: OutputSettings | Mapping[str, Any] | None,
    ) -> None:
        config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
        config = config.sanitized()
        self.output_format_label.set(config.format_label)
        self.jpeg_quality.set(config.jpeg_quality)
        self.output_color_space_label.set(_inverse(COLOR_SPACE_LABELS, config.color_space, "ProPhoto RGB（高保真）"))
        self.output_resize_mode_label.set(_inverse(RESIZE_MODE_LABELS, config.resize_mode, "原始尺寸"))
        self.output_resize_value.set(config.resize_value)
        self.output_allow_upscale.set(config.allow_upscale)
        self.output_resample_label.set(_inverse(RESAMPLE_LABELS, config.resample, "Lanczos（高质量）"))
        self.output_sharpen_label.set(_inverse(SHARPEN_LABELS, config.sharpen, "关闭"))
        self.output_filename_template.set(config.filename_template)
        self.output_collision_label.set(_inverse(COLLISION_LABELS, config.collision_policy, "自动编号"))
        self.output_embed_metadata.set(config.embed_metadata)
        self.output_roll_name.set(config.roll_name)
        self.output_film_stock.set(config.film_stock)
        self.output_camera.set(config.camera)
        self.output_capture_date.set(config.capture_date)
        self.output_frame_number.set(config.frame_number)
        self.output_note.set(config.note)
        self.contact_columns.set(config.contact_columns)
        self.contact_cell_size.set(config.contact_cell_size)
        self.contact_labels.set(config.contact_labels)
        self.contact_background_label.set(_inverse(CONTACT_BACKGROUND_LABELS, config.contact_background, "深色"))
        self._update_output_quality_state()

    def settings_for_item(self: Any, item: Any) -> OutputSettings:
        if getattr(item, "output_settings", None):
            return OutputSettings.from_dict(item.output_settings)
        return self._collect_output_settings()

    def store_current_state(self: Any) -> None:
        original_store_current_state(self)
        item = self.current_item()
        if item is not None:
            item.output_settings = self._collect_output_settings().to_dict()

    def load_index(self: Any, index: int) -> None:
        original_load_index(self, index)
        if 0 <= index < len(self.items):
            self._apply_output_settings_to_ui(self._complete_output_settings_for_item(self.items[index]))

    def open_output_settings_dialog(self: Any) -> None:
        before = self._collect_output_settings()
        dialog = tk.Toplevel(self.root)
        dialog.title("详细输出设置")
        dialog.transient(self.root)
        dialog.geometry("650x610")
        dialog.minsize(590, 540)
        outer = ttk.Frame(dialog, padding=10)
        outer.pack(fill="both", expand=True)
        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)

        quality = ttk.Frame(notebook, padding=12)
        naming = ttk.Frame(notebook, padding=12)
        metadata = ttk.Frame(notebook, padding=12)
        contact = ttk.Frame(notebook, padding=12)
        notebook.add(quality, text="画质与尺寸")
        notebook.add(naming, text="文件命名")
        notebook.add(metadata, text="胶卷信息")
        notebook.add(contact, text="接触印样")

        for frame in (quality, naming, metadata, contact):
            frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(quality, text="输出格式").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            quality,
            textvariable=self.output_format_label,
            values=tuple(FORMAT_SPECS.keys()),
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        ttk.Label(quality, text="JPEG 质量").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Spinbox(quality, from_=1, to=100, textvariable=self.jpeg_quality, width=8).grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        ttk.Label(quality, text="色彩空间").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            quality,
            textvariable=self.output_color_space_label,
            values=tuple(COLOR_SPACE_LABELS.keys()),
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        ttk.Label(quality, text="尺寸模式").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        resize_box = ttk.Combobox(
            quality,
            textvariable=self.output_resize_mode_label,
            values=tuple(RESIZE_MODE_LABELS.keys()),
            state="readonly",
        )
        resize_box.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        ttk.Label(quality, text="尺寸数值").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(quality, textvariable=self.output_resize_value, width=12).grid(row=row, column=1, sticky="w", pady=4)
        row += 1
        ttk.Checkbutton(
            quality,
            text="允许放大超过原始像素尺寸",
            variable=self.output_allow_upscale,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1
        ttk.Label(quality, text="缩放算法").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            quality,
            textvariable=self.output_resample_label,
            values=tuple(RESAMPLE_LABELS.keys()),
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        ttk.Label(quality, text="输出锐化").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            quality,
            textvariable=self.output_sharpen_label,
            values=tuple(SHARPEN_LABELS.keys()),
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", pady=4)
        row += 1
        ttk.Label(
            quality,
            text="尺寸换算在完整正片计算后执行；锐化在最终像素尺寸上执行。",
            foreground="#666",
            wraplength=500,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 0))

        ttk.Label(naming, text="文件名模板").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(naming, textvariable=self.output_filename_template).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(naming, text="重名策略").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            naming,
            textvariable=self.output_collision_label,
            values=tuple(COLLISION_LABELS.keys()),
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(
            naming,
            text=(
                "可用标记：{stem} 原文件名、{sequence} 四位序号、{roll} 胶卷、"
                "{film} 胶卷型号、{frame} 画面编号、{camera} 相机、{date} 日期、{profile} 风格。"
            ),
            foreground="#666",
            wraplength=510,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Checkbutton(
            metadata,
            text="将下列信息写入输出文件元数据",
            variable=self.output_embed_metadata,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        metadata_fields = (
            ("胶卷/批次名称", self.output_roll_name),
            ("胶卷型号", self.output_film_stock),
            ("相机/扫描仪", self.output_camera),
            ("拍摄日期", self.output_capture_date),
            ("画面编号", self.output_frame_number),
            ("备注", self.output_note),
        )
        for row, (label, variable) in enumerate(metadata_fields, start=1):
            ttk.Label(metadata, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            ttk.Entry(metadata, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Label(
            metadata,
            text="拍摄日期建议使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS。信息按图片保存，可通过多图同步复制到整卷。",
            foreground="#666",
            wraplength=510,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Label(contact, text="每行列数").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Spinbox(contact, from_=1, to=12, textvariable=self.contact_columns, width=8).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(contact, text="单格尺寸").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Spinbox(contact, from_=120, to=1200, increment=20, textvariable=self.contact_cell_size, width=8).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Checkbutton(contact, text="显示文件名标签", variable=self.contact_labels).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Label(contact, text="背景").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Combobox(
            contact,
            textvariable=self.contact_background_label,
            values=tuple(CONTACT_BACKGROUND_LABELS.keys()),
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Button(contact, text="立即生成接触印样…", command=self.generate_contact_sheet).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0)
        )

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(10, 0))

        def cancel() -> None:
            self._apply_output_settings_to_ui(before)
            dialog.destroy()

        def apply_and_close() -> None:
            self._store_current_state()
            if hasattr(self, "_schedule_project_save"):
                self._schedule_project_save()
            self.status.set("当前图片的完整输出设置已保存。")
            dialog.destroy()

        ttk.Button(buttons, text="取消", command=cancel).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="保存设置", command=apply_and_close).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.grab_set()

    def task_for_item(self: Any, item: Any, destination: Path) -> CompleteExportTask:
        config = self._complete_output_settings_for_item(item)
        analysis = Analysis.from_dict(item.analysis) if item.analysis else None
        raw = (
            self._raw_settings_for_item(item)
            if hasattr(self, "_raw_settings_for_item")
            else RawDecodeSettings.from_dict(getattr(item, "raw_settings", None))
        )
        return CompleteExportTask(
            source=Path(item.path),
            destination=Path(destination),
            controls=Controls.from_dict(item.controls),
            crop=tuple(item.crop),
            rotation=int(getattr(item, "rotation", 0)),
            geometry=dict(getattr(item, "geometry", {}) or {}),
            analysis=analysis,
            raw_settings=raw,
            bit_depth=config.bit_depth,
            jpeg_quality=config.jpeg_quality,
            label=Path(item.path).name,
            output_settings=config,
        )

    def save_current(self: Any) -> None:
        item = self.current_item()
        if item is None:
            return
        self._store_current_state()
        config = self._complete_output_settings_for_item(item)
        sequence = (self.current_index or 0) + 1
        default_name = render_filename(
            item.path,
            config,
            index=sequence,
            sequence=sequence,
            profile=str(item.controls.get("profile", "")),
        ) + config.extension
        target = filedialog.asksaveasfilename(
            title="保存正片",
            initialfile=default_name,
            defaultextension=config.extension,
            filetypes=[(config.format_name, "*" + config.extension), ("全部文件", "*.*")],
        )
        if not target:
            return
        explicit = replace(config, collision_policy="overwrite")
        task = self._complete_task_for_item(item, Path(target))
        task = replace(task, output_settings=explicit)
        self._submit_export_tasks([task])

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
        reserved: set[str] = set()
        tasks: list[CompleteExportTask] = []
        skipped = 0
        try:
            for sequence, index in enumerate(indices, start=1):
                if index < 0 or index >= len(self.items):
                    continue
                item = self.items[index]
                config = self._complete_output_settings_for_item(item)
                filename = render_filename(
                    item.path,
                    config,
                    index=index + 1,
                    sequence=sequence,
                    profile=str(item.controls.get("profile", "")),
                ) + config.extension
                target = resolve_destination(output_dir / filename, config.collision_policy, reserved)
                if target is None:
                    skipped += 1
                    continue
                tasks.append(self._complete_task_for_item(item, target))
        except Exception as exc:
            messagebox.showerror("无法建立输出任务", str(exc))
            return
        if not tasks:
            messagebox.showinfo("没有需要导出的图片", f"已有文件被跳过：{skipped} 张。")
            return
        self._submit_export_tasks(tasks)
        if skipped:
            self.export_queue_status.set(f"已跳过 {skipped} 个已有文件；准备导出 {len(tasks)} 张图片。")

    def generate_contact_sheet(self: Any) -> None:
        if self._contact_sheet_running:
            messagebox.showinfo("正在生成", "当前接触印样尚未完成。")
            return
        indices = self.selected_indices(default_all=True)
        if not indices:
            return
        self._store_current_state()
        config = self._collect_output_settings()
        roll = config.roll_name.strip() or "PS-Sezhao"
        target = filedialog.asksaveasfilename(
            title="保存接触印样",
            initialfile=f"{roll}_接触印样.jpg",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")],
        )
        if not target:
            return
        snapshots = [deepcopy(self.items[index]) for index in indices if 0 <= index < len(self.items)]
        self._contact_sheet_running = True
        if self.contact_sheet_button is not None:
            self.contact_sheet_button.configure(state="disabled")
        self.status.set(f"正在生成接触印样：0/{len(snapshots)}…")

        def worker() -> None:
            try:
                entries: list[ContactSheetEntry] = []
                for position, item in enumerate(snapshots, start=1):
                    raw = RawDecodeSettings.from_dict(getattr(item, "raw_settings", None))
                    image, metadata = load_image(item.path, raw_settings=raw)
                    image = rotate_array(image, item.rotation)
                    image = apply_photo_geometry(image, GeometrySettings.from_dict(item.geometry))
                    image = crop_array(image, item.crop)
                    source = make_preview(image, max(640, config.contact_cell_size * 2))
                    analysis = Analysis.from_dict(item.analysis) if item.analysis else analyze_image(
                        source,
                        method="crop-border",
                    )
                    result = process_image_tiled(source, analysis, Controls.from_dict(item.controls))
                    result = prepare_save_output(result, metadata)
                    prepared = prepare_output(
                        result,
                        settings_for_contact_sheet(config),
                        source_icc_profile=metadata.get("icc_profile"),
                        source_metadata=metadata,
                    )
                    entries.append(ContactSheetEntry(prepared.image, item.path.name))
                    try:
                        self.root.after(
                            0,
                            lambda done=position: self.status.set(
                                f"正在生成接触印样：{done}/{len(snapshots)}…"
                            ),
                        )
                    except (RuntimeError, tk.TclError):
                        return
                sheet = build_contact_sheet(entries, config)
                target_path = Path(target)
                quality = config.jpeg_quality
                metadata = output_metadata(config)
                metadata["DocumentType"] = "ContactSheet"
                metadata["ImageCount"] = str(len(entries))
                save_output_file(
                    target_path,
                    sheet,
                    bit_depth=8,
                    icc_profile=None,
                    jpeg_quality=quality,
                    metadata=metadata,
                )
                self.root.after(0, lambda: self._finish_contact_sheet(target_path, None))
            except Exception as exc:
                try:
                    self.root.after(0, lambda message=str(exc): self._finish_contact_sheet(None, message))
                except (RuntimeError, tk.TclError):
                    pass

        threading.Thread(target=worker, daemon=True, name="ps-sezhao-contact-sheet").start()

    def finish_contact_sheet(self: Any, target: Path | None, error: str | None) -> None:
        self._contact_sheet_running = False
        if self.contact_sheet_button is not None:
            try:
                self.contact_sheet_button.configure(state="normal")
            except tk.TclError:
                pass
        if error:
            self.status.set("接触印样生成失败。")
            messagebox.showerror("接触印样失败", error)
        elif target is not None:
            self.status.set(f"接触印样已保存：{target}")

    app_class._build_variables = build_variables
    app_class._build_controls_panel = build_controls_panel
    app_class._collect_output_settings = collect_output_settings
    app_class._apply_output_settings_to_ui = apply_output_settings_to_ui
    app_class._complete_output_settings_for_item = settings_for_item
    app_class._store_current_state = store_current_state
    app_class.load_index = load_index
    app_class.open_output_settings_dialog = open_output_settings_dialog
    app_class._complete_task_for_item = task_for_item
    app_class._task_for_item = task_for_item
    app_class.save_current = save_current
    app_class._batch_export = batch_export
    app_class.generate_contact_sheet = generate_contact_sheet
    app_class._finish_contact_sheet = finish_contact_sheet
    _patch_output_queue()
    app_class._complete_output_pipeline_applied = True


def _patch_output_queue() -> None:
    if getattr(OutputQueueService, "_complete_output_applied", False):
        return

    def execute_task(
        self: OutputQueueService,
        batch: Any,
        task: ExportTask,
        *,
        index: int,
        total: int,
    ) -> None:
        self._check_cancel(batch)
        config = (
            task.output_settings
            if isinstance(task, CompleteExportTask) and isinstance(task.output_settings, OutputSettings)
            else OutputSettings.from_dict(
                task.output_settings if isinstance(task, CompleteExportTask) else None
            )
        ).sanitized()
        image, metadata = load_image(task.source, raw_settings=task.raw_settings)
        self._emit_progress(
            batch,
            task,
            index=index,
            total=total,
            stage="geometry",
            item_progress=0.08,
            message=f"应用旋转、拉直、透视与裁切：{task.label}",
        )
        self._check_cancel(batch)
        image = rotate_array(image, task.rotation)
        image = apply_photo_geometry(image, task.geometry)
        source = crop_array(image, task.crop)
        analysis = task.analysis or analyze_image(make_preview(source, 1800), method="crop-border")

        def processing_progress(value: float) -> None:
            progress = 0.18 + min(1.0, max(0.0, float(value))) * 0.57
            self._emit_progress(
                batch,
                task,
                index=index,
                total=total,
                stage="processing",
                item_progress=progress,
                message=f"计算正片 {index}/{total}：{task.label}",
            )

        result = process_image_tiled(
            source,
            analysis,
            task.controls,
            should_cancel=batch.cancel_event.is_set,
            progress_callback=processing_progress,
        )
        self._check_cancel(batch)
        result = prepare_save_output(result, metadata)
        self._emit_progress(
            batch,
            task,
            index=index,
            total=total,
            stage="finalize",
            item_progress=0.80,
            message=f"转换色彩空间、尺寸与锐化：{task.label}",
        )
        prepared = prepare_output(
            result,
            config,
            source_icc_profile=metadata.get("icc_profile"),
            source_metadata=metadata,
        )
        self._check_cancel(batch)
        self._emit_progress(
            batch,
            task,
            index=index,
            total=total,
            stage="saving",
            item_progress=0.92,
            message=f"写入文件：{task.destination.name}",
        )
        _atomic_save_complete(
            task.destination,
            prepared.image,
            settings=config,
            icc_profile=prepared.icc_profile,
            metadata=prepared.metadata,
            should_cancel=batch.cancel_event.is_set,
        )

    OutputQueueService._execute_task = execute_task
    OutputQueueService._complete_output_applied = True


def _atomic_save_complete(
    destination: Path,
    image: Any,
    *,
    settings: OutputSettings,
    icc_profile: bytes | None,
    metadata: Mapping[str, str],
    should_cancel: Any,
) -> None:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if settings.collision_policy in {"error", "skip"} and destination.exists():
        raise FileExistsError(f"输出文件已存在：{destination}")
    temporary = destination.with_name(
        f".{destination.stem}.ps-sezhao-{uuid.uuid4().hex}{destination.suffix}"
    )
    try:
        if should_cancel():
            raise ProcessingCancelled("输出任务已取消。")
        save_output_file(
            temporary,
            image,
            bit_depth=settings.bit_depth,
            icc_profile=icc_profile,
            jpeg_quality=settings.jpeg_quality,
            metadata=metadata,
        )
        if should_cancel():
            raise ProcessingCancelled("输出任务已取消。")
        temporary.replace(destination)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass

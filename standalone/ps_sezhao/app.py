from __future__ import annotations

import argparse
import json
import threading
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from . import __version__
from .engine import Analysis, Controls, PROFILES, analyze_image, neutral_gains, process_image, sample_median_rgb
from .io_utils import load_image, make_preview, save_image
from .jobs import run_job
from .processing import process_image_tiled
from .workspace import (
    FULL_CROP,
    PhotoState,
    clamp_crop,
    crop_array,
    crop_is_full,
    discover_images,
)

CONTROL_SPECS = [
    ("style_strength", "风格强度", 0.0, 2.0, 0.01),
    ("exposure", "曝光 EV", -3.0, 3.0, 0.02),
    ("contrast", "对比度", 0.5, 2.0, 0.01),
    ("gamma", "中间调", 0.5, 2.0, 0.01),
    ("saturation", "饱和度", 0.0, 2.5, 0.01),
    ("temperature", "色温", -3.0, 3.0, 0.02),
    ("tint", "色调（绿↔洋红）", -2.0, 2.0, 0.02),
    ("red_gain", "红色增益", 0.25, 3.0, 0.01),
    ("green_gain", "绿色增益", 0.25, 3.0, 0.01),
    ("blue_gain", "蓝色增益", 0.25, 3.0, 0.01),
    ("black_point", "黑点", -1.0, 1.0, 0.01),
    ("white_point", "白点", -1.0, 1.0, 0.01),
    ("shadows", "阴影", -1.0, 1.0, 0.01),
    ("highlights", "高光", -1.0, 1.0, 0.01),
]
SPEC_BY_KEY = {key: (start, end, step) for key, _label, start, end, step in CONTROL_SPECS}


class SezhaoApp:
    def __init__(self, root: tk.Tk, *, lr_job: str | None = None, initial_files: list[str] | None = None) -> None:
        self.root = root
        self.root.title(f"PS-Sezhao {__version__} · 胶片去色罩")
        self.root.geometry("1460x920")
        self.root.minsize(1080, 720)

        self.lr_job_path = Path(lr_job) if lr_job else None
        self.lr_job_data: dict[str, Any] | None = None

        self.items: list[PhotoState] = []
        self.current_index: int | None = None
        self.full_image: np.ndarray | None = None
        self.preview_source: np.ndarray | None = None
        self.preview_result: np.ndarray | None = None
        self.metadata: dict[str, Any] = {}
        self.analysis: Analysis | None = None
        self.crop_norm = FULL_CROP

        self.photo_image: ImageTk.PhotoImage | None = None
        self.display_pil: Image.Image | None = None
        self.canvas_geometry = (0.0, 0.0, 1.0, 1, 1)
        self.pick_mode: str | None = None
        self.interaction_mode = tk.StringVar(value="pan")
        self.view_fit = True
        self.view_zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.drag_origin: tuple[float, float] | None = None
        self.pan_origin: tuple[float, float, float, float] | None = None
        self.crop_before_drag = FULL_CROP

        self.render_after: str | None = None
        self.render_generation = 0
        self._loading_item = False
        self._tree_updating = False

        self._build_variables()
        self._build_ui()
        self._bind_shortcuts()

        if self.lr_job_path:
            self._load_lr_job(self.lr_job_path)
        elif initial_files:
            self.open_paths([Path(path) for path in initial_files], replace=True)

    def _build_variables(self) -> None:
        self.profile = tk.StringVar(value="generic")
        self.sample_size = tk.IntVar(value=11)
        self.status = tk.StringVar(value="添加一张或多张扫描/翻拍负片开始处理。")
        self.auto_preview = tk.BooleanVar(value=True)
        self.zoom_status = tk.StringVar(value="适应窗口")
        self.crop_status = tk.StringVar(value="裁切：完整画面")
        self.vars: dict[str, tk.DoubleVar] = {
            "style_strength": tk.DoubleVar(value=1.0),
            "exposure": tk.DoubleVar(value=0.0),
            "contrast": tk.DoubleVar(value=1.0),
            "gamma": tk.DoubleVar(value=1.0),
            "saturation": tk.DoubleVar(value=1.0),
            "temperature": tk.DoubleVar(value=0.0),
            "tint": tk.DoubleVar(value=0.0),
            "red_gain": tk.DoubleVar(value=1.0),
            "green_gain": tk.DoubleVar(value=1.0),
            "blue_gain": tk.DoubleVar(value=1.0),
            "black_point": tk.DoubleVar(value=0.0),
            "white_point": tk.DoubleVar(value=0.0),
            "shadows": tk.DoubleVar(value=0.0),
            "highlights": tk.DoubleVar(value=0.0),
        }
        self.entry_vars = {key: tk.StringVar(value=self._format_value(key, var.get())) for key, var in self.vars.items()}

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(10, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(14, weight=1)
        ttk.Button(toolbar, text="添加图像", command=self.open_dialog).grid(row=0, column=0, padx=3)
        ttk.Button(toolbar, text="添加文件夹", command=self.open_folder_dialog).grid(row=0, column=1, padx=3)
        ttk.Button(toolbar, text="移除选中", command=self.remove_selected).grid(row=0, column=2, padx=3)
        ttk.Separator(toolbar, orient="vertical").grid(row=0, column=3, sticky="ns", padx=6)
        ttk.Button(toolbar, text="上一张", command=lambda: self.step_item(-1)).grid(row=0, column=4, padx=3)
        ttk.Button(toolbar, text="下一张", command=lambda: self.step_item(1)).grid(row=0, column=5, padx=3)
        ttk.Button(toolbar, text="自动分析边框", command=self.auto_analyze).grid(row=0, column=6, padx=(12, 3))
        ttk.Button(toolbar, text="吸管：胶片基底", command=lambda: self.start_pick("base")).grid(row=0, column=7, padx=3)
        ttk.Button(toolbar, text="吸管：中性色", command=lambda: self.start_pick("neutral")).grid(row=0, column=8, padx=3)
        ttk.Label(toolbar, text="取样").grid(row=0, column=9, padx=(10, 3))
        ttk.Combobox(toolbar, textvariable=self.sample_size, values=(1, 3, 5, 11, 21), width=5, state="readonly").grid(row=0, column=10)
        ttk.Checkbutton(toolbar, text="自动预览", variable=self.auto_preview).grid(row=0, column=11, padx=8)
        ttk.Button(toolbar, text="恢复默认", command=self.reset_controls).grid(row=0, column=12, padx=3)
        ttk.Separator(toolbar, orient="vertical").grid(row=0, column=13, sticky="ns", padx=6)
        ttk.Label(toolbar, textvariable=self.status, anchor="e").grid(row=0, column=14, sticky="ew", padx=(8, 3))

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew")

        list_panel = ttk.Frame(body, padding=(8, 8, 4, 8))
        preview_frame = ttk.Frame(body, padding=8)
        controls_outer = ttk.Frame(body, padding=(4, 8, 8, 8))
        body.add(list_panel, weight=1)
        body.add(preview_frame, weight=5)
        body.add(controls_outer, weight=2)

        self._build_file_panel(list_panel)
        self._build_preview_panel(preview_frame)
        self._build_controls_panel(controls_outer)

    def _build_file_panel(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)
        ttk.Label(parent, text="图片列表", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.file_tree = ttk.Treeview(
            parent,
            columns=("index", "name", "crop"),
            show="headings",
            selectmode="extended",
            height=20,
        )
        self.file_tree.heading("index", text="#")
        self.file_tree.heading("name", text="文件")
        self.file_tree.heading("crop", text="裁切")
        self.file_tree.column("index", width=34, stretch=False, anchor="center")
        self.file_tree.column("name", width=180, stretch=True)
        self.file_tree.column("crop", width=78, stretch=False, anchor="center")
        list_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=list_scroll.set)
        self.file_tree.grid(row=1, column=0, sticky="nsew")
        list_scroll.grid(row=1, column=1, sticky="ns")
        self.file_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.file_tree.bind("<Double-1>", self.on_tree_select)

        buttons = ttk.Frame(parent)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(buttons, text="同步参数到选中", command=self.sync_controls_selected).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(buttons, text="同步裁切到选中", command=self.sync_crop_selected).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        ttk.Button(buttons, text="全选", command=self.select_all_items).grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=(4, 0))
        ttk.Button(buttons, text="清空列表", command=self.clear_items).grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=(4, 0))

    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        viewbar = ttk.Frame(parent)
        viewbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        viewbar.columnconfigure(12, weight=1)
        ttk.Label(viewbar, text="工具").grid(row=0, column=0, padx=(0, 4))
        ttk.Radiobutton(viewbar, text="平移", value="pan", variable=self.interaction_mode, command=self._update_cursor).grid(row=0, column=1)
        ttk.Radiobutton(viewbar, text="裁切", value="crop", variable=self.interaction_mode, command=self._update_cursor).grid(row=0, column=2)
        ttk.Button(viewbar, text="重置裁切", command=self.reset_crop).grid(row=0, column=3, padx=(6, 10))
        ttk.Separator(viewbar, orient="vertical").grid(row=0, column=4, sticky="ns", padx=5)
        ttk.Button(viewbar, text="−", width=3, command=lambda: self.zoom_by(1 / 1.25)).grid(row=0, column=5)
        ttk.Button(viewbar, text="+", width=3, command=lambda: self.zoom_by(1.25)).grid(row=0, column=6, padx=(3, 0))
        ttk.Button(viewbar, text="适应", command=self.zoom_fit_view).grid(row=0, column=7, padx=(6, 3))
        ttk.Button(viewbar, text="100%", command=self.zoom_actual).grid(row=0, column=8, padx=3)
        ttk.Button(viewbar, text="200%", command=lambda: self.set_zoom(2.0)).grid(row=0, column=9, padx=3)
        ttk.Label(viewbar, textvariable=self.zoom_status).grid(row=0, column=10, padx=(10, 3))
        ttk.Label(viewbar, textvariable=self.crop_status, anchor="e").grid(row=0, column=12, sticky="e")

        self.canvas = tk.Canvas(parent, bg="#191919", highlightthickness=0, cursor="hand2")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", lambda event: self.on_mousewheel(event, direction=1))
        self.canvas.bind("<Button-5>", lambda event: self.on_mousewheel(event, direction=-1))
        self.canvas.bind("<Configure>", lambda _event: self.draw_preview())

        hint = ttk.Label(
            parent,
            text="滚轮缩放；平移模式拖动画面；裁切模式拖出矩形。裁切仅在导出时应用，不修改原文件。",
            foreground="#666",
        )
        hint.grid(row=2, column=0, sticky="w", pady=(5, 0))

    def _build_controls_panel(self, parent: ttk.Frame) -> None:
        controls_canvas = tk.Canvas(parent, width=340, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=controls_canvas.yview)
        self.controls = ttk.Frame(controls_canvas)
        self.controls.bind("<Configure>", lambda _event: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")))
        controls_canvas.create_window((0, 0), window=self.controls, anchor="nw", width=326)
        controls_canvas.configure(yscrollcommand=scrollbar.set)
        controls_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0
        ttk.Label(self.controls, text="胶片起始配置", font=("TkDefaultFont", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(2, 4))
        row += 1
        profile_box = ttk.Combobox(self.controls, textvariable=self.profile, state="readonly", width=30)
        profile_box["values"] = tuple(PROFILES.keys())
        profile_box.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1
        profile_box.bind("<<ComboboxSelected>>", lambda _event: self._control_changed())

        for key, label, start, end, resolution in CONTROL_SPECS:
            row = self._add_scale(row, key, label, start, end, resolution)

        sync_frame = ttk.LabelFrame(self.controls, text="多图同步", padding=6)
        sync_frame.grid(row=row, column=0, sticky="ew", pady=(10, 4))
        row += 1
        sync_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(sync_frame, text="参数 → 选中图片", command=self.sync_controls_selected).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(sync_frame, text="裁切 → 选中图片", command=self.sync_crop_selected).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        action_frame = ttk.LabelFrame(self.controls, text="输出", padding=6)
        action_frame.grid(row=row, column=0, sticky="ew", pady=(8, 4))
        row += 1
        action_frame.columnconfigure((0, 1), weight=1)
        ttk.Button(action_frame, text="保存当前", command=self.save_current).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(action_frame, text="导出选中", command=self.export_selected).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        ttk.Button(action_frame, text="导出全部", command=self.export_all).grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=(4, 0))
        ttk.Button(action_frame, text="LR 批量应用并完成", command=self.apply_all).grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=(4, 0))

        ttk.Label(
            self.controls,
            text="数字框可直接输入；− / + 按当前参数步长微调。按 Enter 或移开焦点后生效。",
            foreground="#666",
            wraplength=300,
        ).grid(row=row, column=0, sticky="w", pady=(7, 12))

    def _add_scale(self, row: int, key: str, label: str, start: float, end: float, resolution: float) -> int:
        frame = ttk.Frame(self.controls)
        frame.grid(row=row, column=0, sticky="ew", pady=3)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text=label).grid(row=0, column=0, sticky="w")
        stepper = ttk.Frame(frame)
        stepper.grid(row=0, column=1, sticky="e")
        minus = ttk.Button(stepper, text="−", width=3, command=lambda k=key: self.adjust_control(k, -1))
        entry = ttk.Entry(stepper, textvariable=self.entry_vars[key], width=8, justify="right")
        plus = ttk.Button(stepper, text="+", width=3, command=lambda k=key: self.adjust_control(k, 1))
        minus.grid(row=0, column=0)
        entry.grid(row=0, column=1, padx=2)
        plus.grid(row=0, column=2)
        entry.bind("<Return>", lambda _event, k=key: self.commit_entry(k))
        entry.bind("<FocusOut>", lambda _event, k=key: self.commit_entry(k))
        entry.bind("<Up>", lambda _event, k=key: self.adjust_control(k, 1))
        entry.bind("<Down>", lambda _event, k=key: self.adjust_control(k, -1))

        scale = tk.Scale(
            frame,
            from_=start,
            to=end,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            variable=self.vars[key],
            showvalue=False,
            highlightthickness=0,
            command=lambda _value, k=key: self.on_scale(k),
        )
        scale.grid(row=1, column=0, columnspan=2, sticky="ew")
        return row + 1

    def _bind_shortcuts(self) -> None:
        self.root.bind_all("<Control-o>", lambda _event: self.open_dialog())
        self.root.bind_all("<Control-0>", lambda _event: self.zoom_fit_view())
        self.root.bind_all("<Control-1>", lambda _event: self.zoom_actual())
        self.root.bind_all("<Control-plus>", lambda _event: self.zoom_by(1.25))
        self.root.bind_all("<Control-minus>", lambda _event: self.zoom_by(1 / 1.25))

    def _format_value(self, key: str, value: float) -> str:
        _minimum, _maximum, step = SPEC_BY_KEY[key]
        decimals = 3 if step < 0.01 else 2
        return f"{float(value):.{decimals}f}"

    def on_scale(self, key: str) -> None:
        self.entry_vars[key].set(self._format_value(key, self.vars[key].get()))
        self._control_changed()

    def commit_entry(self, key: str) -> str:
        minimum, maximum, _step = SPEC_BY_KEY[key]
        try:
            value = float(self.entry_vars[key].get().strip())
        except (TypeError, ValueError):
            value = self.vars[key].get()
        value = min(maximum, max(minimum, value))
        self.vars[key].set(value)
        self.entry_vars[key].set(self._format_value(key, value))
        self._control_changed()
        return "break"

    def adjust_control(self, key: str, direction: int) -> str:
        minimum, maximum, step = SPEC_BY_KEY[key]
        value = min(maximum, max(minimum, self.vars[key].get() + step * int(direction)))
        self.vars[key].set(round(value, 6))
        self.entry_vars[key].set(self._format_value(key, value))
        self._control_changed()
        return "break"

    def _control_changed(self) -> None:
        if self._loading_item:
            return
        self._store_current_state()
        self.schedule_render()

    def controls_value(self) -> Controls:
        return Controls(profile=self.profile.get(), **{key: variable.get() for key, variable in self.vars.items()}).sanitized()

    def apply_controls(self, controls: Controls) -> None:
        self._loading_item = True
        try:
            self.profile.set(controls.profile)
            for key, variable in self.vars.items():
                value = float(getattr(controls, key))
                variable.set(value)
                self.entry_vars[key].set(self._format_value(key, value))
        finally:
            self._loading_item = False

    def reset_controls(self) -> None:
        self.apply_controls(Controls())
        self._store_current_state()
        self.schedule_render(0)

    def current_item(self) -> PhotoState | None:
        if self.current_index is None or self.current_index < 0 or self.current_index >= len(self.items):
            return None
        return self.items[self.current_index]

    def _store_current_state(self) -> None:
        item = self.current_item()
        if item is None:
            return
        item.controls = self.controls_value().to_dict()
        item.analysis = self.analysis.to_dict() if self.analysis else None
        item.crop = clamp_crop(self.crop_norm)
        self._update_tree_row(self.current_index)

    def open_dialog(self) -> None:
        paths = filedialog.askopenfilenames(
            title="添加扫描或翻拍负片",
            filetypes=[("图像", "*.tif *.tiff *.jpg *.jpeg *.png *.bmp *.webp"), ("全部文件", "*.*")],
        )
        if paths:
            self.open_paths([Path(path) for path in paths])

    def open_folder_dialog(self) -> None:
        folder = filedialog.askdirectory(title="选择图像文件夹")
        if not folder:
            return
        recursive = messagebox.askyesno("包含子文件夹", "是否同时添加子文件夹中的图像？")
        try:
            paths = discover_images(folder, recursive=recursive)
        except Exception as error:
            messagebox.showerror("无法读取文件夹", str(error))
            return
        if not paths:
            messagebox.showinfo("没有图像", "所选文件夹中没有支持的图像。")
            return
        self.open_paths(paths)

    def open_paths(self, paths: list[Path], *, replace: bool = False) -> None:
        valid = [Path(path) for path in paths if Path(path).suffix.lower() in {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}]
        if not valid:
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

    def refresh_file_tree(self) -> None:
        self._tree_updating = True
        try:
            self.file_tree.delete(*self.file_tree.get_children())
            for index, item in enumerate(self.items):
                self.file_tree.insert("", "end", iid=str(index), values=(index + 1, item.path.name, item.crop_label))
            if self.current_index is not None and self.current_index < len(self.items):
                self.file_tree.selection_add(str(self.current_index))
                self.file_tree.focus(str(self.current_index))
                self.file_tree.see(str(self.current_index))
        finally:
            self._tree_updating = False

    def _update_tree_row(self, index: int) -> None:
        if index < 0 or index >= len(self.items):
            return
        iid = str(index)
        if self.file_tree.exists(iid):
            item = self.items[index]
            self.file_tree.item(iid, values=(index + 1, item.path.name, item.crop_label))

    def selected_indices(self, *, default_all: bool = False) -> list[int]:
        values = sorted({int(iid) for iid in self.file_tree.selection() if str(iid).isdigit()})
        if not values and self.current_index is not None:
            values = [self.current_index]
        if default_all and len(values) <= 1:
            return list(range(len(self.items)))
        return [index for index in values if 0 <= index < len(self.items)]

    def on_tree_select(self, _event: tk.Event | None = None) -> None:
        if self._tree_updating:
            return
        focus = self.file_tree.focus()
        if not focus:
            selection = self.file_tree.selection()
            focus = selection[0] if selection else ""
        if not str(focus).isdigit():
            return
        index = int(focus)
        if index != self.current_index:
            self.load_index(index)

    def load_index(self, index: int) -> None:
        if index < 0 or index >= len(self.items):
            return
        self._store_current_state()
        item = self.items[index]
        try:
            self._loading_item = True
            self.status.set(f"正在读取 {item.path.name}…")
            self.root.update_idletasks()
            image, metadata = load_image(item.path)
            self.current_index = index
            self.full_image = image
            self.preview_source = make_preview(image, 1800)
            self.preview_result = None
            self.metadata = metadata
            self.crop_norm = clamp_crop(item.crop)
            self.analysis = Analysis.from_dict(item.analysis) if item.analysis else None
            self.apply_controls(Controls.from_dict(item.controls))
            self.zoom_fit_view()
            self._set_display_image(self.preview_source)
            self._tree_updating = True
            self.file_tree.selection_add(str(index))
            self.file_tree.focus(str(index))
            self.file_tree.see(str(index))
            self._tree_updating = False
            self._update_crop_status()
        except Exception as error:
            messagebox.showerror("无法打开图像", str(error))
            self.status.set("打开失败。")
            return
        finally:
            self._loading_item = False

        if self.analysis is None:
            self.auto_analyze()
        else:
            self.status.set(f"已载入 {item.path.name} 的保存参数。")
            self.schedule_render(0)

    def step_item(self, direction: int) -> None:
        if not self.items:
            return
        index = self.current_index if self.current_index is not None else 0
        self.load_index((index + direction) % len(self.items))

    def remove_selected(self) -> None:
        indices = self.selected_indices()
        if not indices:
            return
        if not messagebox.askyesno("移除图片", f"从当前列表移除 {len(indices)} 张图片？不会删除原文件。"):
            return
        self._store_current_state()
        remaining = [item for index, item in enumerate(self.items) if index not in set(indices)]
        self.items = remaining
        self.current_index = None
        self.refresh_file_tree()
        if self.items:
            self.load_index(min(indices[0], len(self.items) - 1))
        else:
            self._clear_current_display()

    def clear_items(self) -> None:
        if not self.items:
            return
        if not messagebox.askyesno("清空列表", "清空当前图片列表？不会删除原文件。"):
            return
        self.items.clear()
        self.current_index = None
        self.refresh_file_tree()
        self._clear_current_display()

    def _clear_current_display(self) -> None:
        self.full_image = None
        self.preview_source = None
        self.preview_result = None
        self.display_pil = None
        self.analysis = None
        self.crop_norm = FULL_CROP
        self.canvas.delete("all")
        self.status.set("图片列表为空。")
        self._update_crop_status()

    def select_all_items(self) -> None:
        if self.items:
            self.file_tree.selection_set([str(index) for index in range(len(self.items))])

    def sync_controls_selected(self) -> None:
        if not self.items:
            return
        self._store_current_state()
        controls = self.controls_value().to_dict()
        indices = self.selected_indices()
        for index in indices:
            self.items[index].controls = dict(controls)
        self.status.set(f"已将当前参数同步到 {len(indices)} 张选中图片。")

    def sync_crop_selected(self) -> None:
        if not self.items:
            return
        self._store_current_state()
        crop = clamp_crop(self.crop_norm)
        indices = self.selected_indices()
        for index in indices:
            self.items[index].crop = crop
            self._update_tree_row(index)
        self.status.set(f"已将当前裁切同步到 {len(indices)} 张选中图片。")

    def auto_analyze(self) -> None:
        if self.preview_source is None:
            return
        try:
            self.status.set("正在分析胶片边框…")
            self.analysis = analyze_image(self.preview_source, border_fraction=0.07)
            self._store_current_state()
            self.status.set(f"基底分析完成，可信度 {self.analysis.confidence * 100:.0f}%")
            self.schedule_render(0)
        except Exception as error:
            self.analysis = None
            self._set_display_image(self.preview_source)
            messagebox.showwarning("自动分析失败", f"{error}\n\n请点击“吸管：胶片基底”，再点击未曝光的橙色边框。")
            self.status.set("请使用胶片基底吸管。")

    def start_pick(self, mode: str) -> None:
        if self.preview_source is None:
            messagebox.showinfo("尚未打开图像", "请先添加并选择一张负片图像。")
            return
        if mode == "neutral" and self.analysis is None:
            messagebox.showinfo("尚未转正", "请先分析或吸取胶片基底。")
            return
        self.pick_mode = mode
        self.canvas.configure(cursor="crosshair")
        self.status.set("请点击未曝光橙色边框。" if mode == "base" else "请点击白色、灰色或应为中性的区域。")

    def _update_cursor(self) -> None:
        if self.pick_mode or self.interaction_mode.get() == "crop":
            self.canvas.configure(cursor="crosshair")
        else:
            self.canvas.configure(cursor="hand2")

    def map_canvas_to_preview(self, canvas_x: float, canvas_y: float) -> tuple[float, float] | None:
        offset_x, offset_y, scale, width, height = self.canvas_geometry
        if scale <= 0:
            return None
        x = (canvas_x - offset_x) / scale
        y = (canvas_y - offset_y) / scale
        if x < 0 or y < 0 or x >= width or y >= height:
            return None
        return x, y

    def on_canvas_press(self, event: tk.Event) -> None:
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
            self.crop_norm = self._crop_from_points(point, point)
            self.draw_preview()
        else:
            self.pan_origin = (float(event.x), float(event.y), self.pan_x, self.pan_y)
            self.canvas.configure(cursor="fleur")

    def on_canvas_motion(self, event: tk.Event) -> None:
        if self.drag_origin is not None and self.interaction_mode.get() == "crop":
            point = self.map_canvas_to_preview(event.x, event.y)
            if point is None:
                point = self._clamped_canvas_point(event.x, event.y)
            if point is not None:
                self.crop_norm = self._crop_from_points(self.drag_origin, point)
                self._update_crop_status()
                self.draw_preview()
            return
        if self.pan_origin is not None:
            start_x, start_y, original_x, original_y = self.pan_origin
            self.pan_x = original_x + float(event.x) - start_x
            self.pan_y = original_y + float(event.y) - start_y
            self.view_fit = False
            self.draw_preview()

    def on_canvas_release(self, _event: tk.Event) -> None:
        if self.drag_origin is not None:
            left, top, right, bottom = clamp_crop(self.crop_norm)
            if right - left < 0.005 or bottom - top < 0.005:
                self.crop_norm = self.crop_before_drag
            self.drag_origin = None
            self._store_current_state()
            self._update_crop_status()
            self.draw_preview()
        self.pan_origin = None
        self._update_cursor()

    def _clamped_canvas_point(self, canvas_x: float, canvas_y: float) -> tuple[float, float] | None:
        offset_x, offset_y, scale, width, height = self.canvas_geometry
        if scale <= 0:
            return None
        x = min(width - 1, max(0.0, (canvas_x - offset_x) / scale))
        y = min(height - 1, max(0.0, (canvas_y - offset_y) / scale))
        return x, y

    def _crop_from_points(self, start: tuple[float, float], end: tuple[float, float]) -> tuple[float, float, float, float]:
        if self.preview_source is None:
            return FULL_CROP
        height, width, _ = self.preview_source.shape
        left = min(start[0], end[0]) / width
        right = max(start[0], end[0]) / width
        top = min(start[1], end[1]) / height
        bottom = max(start[1], end[1]) / height
        return clamp_crop((left, top, right, bottom))

    def _apply_pick(self, x: int, y: int) -> None:
        if self.preview_source is None:
            return
        try:
            if self.pick_mode == "base":
                base = sample_median_rgb(self.preview_source, x, y, self.sample_size.get())
                self.analysis = analyze_image(self.preview_source, base=base, method="eyedropper")
                self.status.set("胶片基底已更新，正在刷新预览。")
            else:
                assert self.analysis is not None
                gains = neutral_gains(self.preview_source, self.analysis, self.controls_value(), x, y, self.sample_size.get())
                for key, value in zip(("red_gain", "green_gain", "blue_gain"), gains):
                    self.vars[key].set(value)
                    self.entry_vars[key].set(self._format_value(key, value))
                self.status.set("中性色校正完成，正在刷新预览。")
            self.pick_mode = None
            self._update_cursor()
            self._store_current_state()
            self.schedule_render(0)
        except Exception as error:
            messagebox.showerror("取样失败", str(error))

    def schedule_render(self, delay: int = 120) -> None:
        if not self.auto_preview.get() or self.analysis is None or self.preview_source is None:
            return
        if self.render_after:
            self.root.after_cancel(self.render_after)
        self.render_after = self.root.after(delay, self.render_preview)

    def render_preview(self) -> None:
        self.render_after = None
        if self.analysis is None or self.preview_source is None:
            return
        self.render_generation += 1
        generation = self.render_generation
        controls = self.controls_value()
        analysis = self.analysis
        source = self.preview_source.copy()
        self.status.set("正在更新大图预览…")

        def worker() -> None:
            try:
                result = process_image(source, analysis, controls)
                self.root.after(0, lambda: self._accept_render(generation, result))
            except Exception as error:
                trace = traceback.format_exc()
                self.root.after(0, lambda: self._render_error(error, trace))

        threading.Thread(target=worker, daemon=True).start()

    def _accept_render(self, generation: int, result: np.ndarray) -> None:
        if generation != self.render_generation:
            return
        self.preview_result = result
        self._set_display_image(result)
        self.status.set("预览已更新；可缩放、平移、裁切或继续调色。")

    def _render_error(self, error: Exception, trace: str) -> None:
        print(trace)
        self.status.set(f"预览失败：{error}")

    def _set_display_image(self, image: np.ndarray | None) -> None:
        if image is None:
            self.display_pil = None
            self.canvas.delete("all")
            return
        data8 = np.round(np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
        self.display_pil = Image.fromarray(data8, mode="RGB")
        self.draw_preview()

    def draw_preview(self) -> None:
        if self.display_pil is None:
            self.canvas.delete("all")
            return
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        width, height = self.display_pil.size
        fit_scale = min(canvas_width / width, canvas_height / height)
        if self.view_fit:
            scale = fit_scale
            self.view_zoom = scale
            self.pan_x = 0.0
            self.pan_y = 0.0
        else:
            scale = min(8.0, max(0.03, self.view_zoom))
        target_width = width * scale
        target_height = height * scale
        offset_x = (canvas_width - target_width) / 2.0 + self.pan_x
        offset_y = (canvas_height - target_height) / 2.0 + self.pan_y
        self.canvas_geometry = (offset_x, offset_y, scale, width, height)

        source_left = max(0.0, (0.0 - offset_x) / scale)
        source_top = max(0.0, (0.0 - offset_y) / scale)
        source_right = min(float(width), (canvas_width - offset_x) / scale)
        source_bottom = min(float(height), (canvas_height - offset_y) / scale)

        self.canvas.delete("all")
        if source_right > source_left and source_bottom > source_top:
            x0 = max(0, int(np.floor(source_left)))
            y0 = max(0, int(np.floor(source_top)))
            x1 = min(width, max(x0 + 1, int(np.ceil(source_right))))
            y1 = min(height, max(y0 + 1, int(np.ceil(source_bottom))))
            viewport = self.display_pil.crop((x0, y0, x1, y1))
            rendered_width = max(1, round((x1 - x0) * scale))
            rendered_height = max(1, round((y1 - y0) * scale))
            if viewport.size != (rendered_width, rendered_height):
                viewport = viewport.resize((rendered_width, rendered_height), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(viewport)
            draw_x = offset_x + x0 * scale
            draw_y = offset_y + y0 * scale
            self.canvas.create_image(draw_x, draw_y, anchor="nw", image=self.photo_image)

        self._draw_crop_overlay()
        self.zoom_status.set("适应窗口" if self.view_fit else f"{scale * 100:.0f}%")

    def _draw_crop_overlay(self) -> None:
        if self.display_pil is None:
            return
        offset_x, offset_y, scale, width, height = self.canvas_geometry
        left, top, right, bottom = clamp_crop(self.crop_norm)
        x0 = offset_x + left * width * scale
        y0 = offset_y + top * height * scale
        x1 = offset_x + right * width * scale
        y1 = offset_y + bottom * height * scale
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if not crop_is_full(self.crop_norm) or self.interaction_mode.get() == "crop":
            overlay = {"fill": "#000000", "stipple": "gray50", "outline": ""}
            self.canvas.create_rectangle(0, 0, canvas_width, max(0, y0), **overlay)
            self.canvas.create_rectangle(0, min(canvas_height, y1), canvas_width, canvas_height, **overlay)
            self.canvas.create_rectangle(0, max(0, y0), max(0, x0), min(canvas_height, y1), **overlay)
            self.canvas.create_rectangle(min(canvas_width, x1), max(0, y0), canvas_width, min(canvas_height, y1), **overlay)
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="#ffd35a", width=2)
            size = 5
            for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                self.canvas.create_rectangle(x - size, y - size, x + size, y + size, fill="#ffd35a", outline="#222222")

    def on_mousewheel(self, event: tk.Event, direction: int | None = None) -> str:
        if self.display_pil is None:
            return "break"
        if direction is None:
            direction = 1 if getattr(event, "delta", 0) > 0 else -1
        factor = 1.15 if direction > 0 else 1 / 1.15
        self.zoom_at(float(event.x), float(event.y), factor)
        return "break"

    def zoom_at(self, canvas_x: float, canvas_y: float, factor: float) -> None:
        if self.display_pil is None:
            return
        offset_x, offset_y, old_scale, width, height = self.canvas_geometry
        image_x = (canvas_x - offset_x) / old_scale
        image_y = (canvas_y - offset_y) / old_scale
        new_scale = min(8.0, max(0.03, old_scale * factor))
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        centered_x = (canvas_width - width * new_scale) / 2.0
        centered_y = (canvas_height - height * new_scale) / 2.0
        self.pan_x = canvas_x - image_x * new_scale - centered_x
        self.pan_y = canvas_y - image_y * new_scale - centered_y
        self.view_fit = False
        self.view_zoom = new_scale
        self.draw_preview()

    def zoom_by(self, factor: float) -> None:
        self.zoom_at(self.canvas.winfo_width() / 2.0, self.canvas.winfo_height() / 2.0, factor)

    def zoom_fit_view(self) -> None:
        self.view_fit = True
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.draw_preview()

    def zoom_actual(self) -> None:
        self.set_zoom(1.0)

    def set_zoom(self, scale: float) -> None:
        self.view_fit = False
        self.view_zoom = min(8.0, max(0.03, float(scale)))
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.draw_preview()

    def reset_crop(self) -> None:
        self.crop_norm = FULL_CROP
        self._store_current_state()
        self._update_crop_status()
        self.draw_preview()

    def _update_crop_status(self) -> None:
        if crop_is_full(self.crop_norm):
            self.crop_status.set("裁切：完整画面")
        else:
            left, top, right, bottom = clamp_crop(self.crop_norm)
            self.crop_status.set(f"裁切：{(right - left) * 100:.0f}% × {(bottom - top) * 100:.0f}%")

    def save_current(self) -> None:
        if self.full_image is None or self.analysis is None or self.current_item() is None:
            return
        self._store_current_state()
        item = self.current_item()
        assert item is not None
        default_name = item.path.stem + "_PS-Sezhao.tif"
        target = filedialog.asksaveasfilename(
            title="保存正片",
            initialfile=default_name,
            defaultextension=".tif",
            filetypes=[("16 位 TIFF", "*.tif"), ("JPEG", "*.jpg"), ("PNG", "*.png")],
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

    def _process_and_save(
        self,
        image: np.ndarray,
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
                save_image(target, result, bit_depth=16, icc_profile=metadata.get("icc_profile"))
                self.root.after(0, lambda: self.status.set(f"已保存：{target}"))
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("保存失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def export_selected(self) -> None:
        self._batch_export(self.selected_indices())

    def export_all(self) -> None:
        self._batch_export(list(range(len(self.items))))

    def _batch_export(self, indices: list[int]) -> None:
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
        self.status.set(f"正在批量处理 {len(states)} 张照片…")

        def worker() -> None:
            try:
                for position, item in enumerate(states, start=1):
                    image, metadata = load_image(item.path)
                    analysis = Analysis.from_dict(item.analysis) if item.analysis else analyze_image(image)
                    controls = Controls.from_dict(item.controls)
                    source = crop_array(image, item.crop)
                    result = process_image_tiled(source, analysis, controls)
                    target = output_dir / f"{item.path.stem}_PS-Sezhao.tif"
                    save_image(target, result, bit_depth=16, icc_profile=metadata.get("icc_profile"))
                    self.root.after(
                        0,
                        lambda i=position, name=item.path.name: self.status.set(f"正在处理 {i}/{len(states)}：{name}"),
                    )
                self.root.after(0, lambda: self.status.set(f"批量处理完成：{output_dir}"))
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("批量处理失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def apply_all(self) -> None:
        if self.lr_job_data is not None and self.lr_job_path is not None:
            self._run_lr_job()
        else:
            self.export_all()

    def _load_lr_job(self, job_path: Path) -> None:
        try:
            data = json.loads(job_path.read_text(encoding="utf-8"))
            self.lr_job_data = data
            items = data.get("items") or []
            if not items:
                raise ValueError("Lightroom 任务中没有照片。")
            self.open_paths([Path(item["input"]) for item in items], replace=True)
            self.status.set(f"Lightroom 已发送 {len(items)} 张照片。调整后点击“LR 批量应用并完成”。")
        except Exception as error:
            messagebox.showerror("无法读取 Lightroom 任务", str(error))

    def _run_lr_job(self) -> None:
        if self.lr_job_data is None or self.lr_job_path is None or self.analysis is None:
            messagebox.showinfo("尚未分析", "请先分析或吸取胶片基底。")
            return
        self._store_current_state()
        self.lr_job_data.setdefault("settings", {})["analysis"] = self.analysis.to_dict()
        self.lr_job_data["settings"]["controls"] = self.controls_value().to_dict()
        self.lr_job_data["settings"]["crop"] = list(clamp_crop(self.crop_norm))
        self.lr_job_path.write_text(json.dumps(self.lr_job_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status.set("正在生成 Lightroom 正片文件…")

        def progress(done: int, total: int, name: str) -> None:
            self.root.after(0, lambda: self.status.set(f"Lightroom 批量处理 {done}/{total}：{name}"))

        def worker() -> None:
            try:
                run_job(self.lr_job_path, progress)
                self.root.after(0, self._finish_lr_job)
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror("Lightroom 处理失败", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_lr_job(self) -> None:
        self.status.set("Lightroom 正片已生成，正在返回目录。")
        self.root.after(400, self.root.destroy)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PS-Sezhao 胶片去色罩")
    parser.add_argument("files", nargs="*", help="启动时打开的图像")
    parser.add_argument("--lr-job", help="由 Lightroom Classic 创建的任务 JSON")
    parser.add_argument("--batch-job", help="无界面执行任务 JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.batch_job:
        run_job(args.batch_job)
        return 0
    root = tk.Tk()
    SezhaoApp(root, lr_job=args.lr_job, initial_files=args.files)
    root.mainloop()
    return 0

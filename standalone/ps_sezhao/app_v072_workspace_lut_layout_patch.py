from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .core.lut import (
    list_cube_luts,
    load_cube_lut,
    resolve_user_lut,
    safe_lut_filename,
)
from .engine import Controls
from .engine_style_v060_patch import (
    FILM_PROFILE_ORDER,
    FILM_PROFILES,
    SCANNER_PROFILES,
    canonical_scanner_profile,
)
from .storage.paths import default_lut_directory, default_project_directory


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def _widget_text(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("text"))
    except (AttributeError, tk.TclError):
        return ""


def _widget_variable(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("textvariable"))
    except (AttributeError, tk.TclError):
        return ""


def _open_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def apply_v072_workspace_lut_layout_patch(app_class: Type[Any]) -> None:
    """Add bounded style selectors, framed tools and portable user LUT actions."""

    if getattr(app_class, "_v072_workspace_lut_layout_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_ui = app_class._build_ui
    original_controls_value = app_class.controls_value
    original_apply_controls = app_class.apply_controls
    original_style_selected = app_class._style_selected
    original_update_style_library_text = app_class._update_style_library_text

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.user_lut_file = tk.StringVar(value="")
        self.lut_directory_text = tk.StringVar(value=f"LUT 文件夹：{default_lut_directory()}")
        self._user_lut_label_to_file: dict[str, str] = {}
        self._user_lut_file_to_label: dict[str, str] = {}
        self.scanner_profile_box: ttk.Combobox | None = None
        self.film_profile_box: ttk.Combobox | None = None

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._configure_style_selector_layout()
        self._rebuild_framed_preview_toolbar()
        self._rebuild_framed_geometry_toolbar()
        self._add_project_folder_action()
        self.root.after_idle(self._refresh_user_lut_library)

    def configure_style_selector_layout(self: Any) -> None:
        frame = next(
            (
                widget
                for widget in _walk_widgets(self.controls)
                if isinstance(widget, ttk.LabelFrame)
                and _widget_text(widget).startswith("扫描仪与胶卷风格")
            ),
            None,
        )
        if frame is None:
            return
        self.style_library_frame = frame
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

        description_label = None
        notice_label = None
        for widget in frame.winfo_children():
            if isinstance(widget, ttk.Combobox):
                variable = _widget_variable(widget)
                if variable == str(self.scanner_profile_label):
                    self.scanner_profile_box = widget
                elif variable == str(self.film_profile_label):
                    self.film_profile_box = widget
            elif isinstance(widget, ttk.Label):
                variable = _widget_variable(widget)
                if variable == str(self.style_description):
                    description_label = widget
                elif "非官方风格参考" in _widget_text(widget):
                    notice_label = widget

        for box in (self.scanner_profile_box, self.film_profile_box):
            if box is None:
                continue
            # A large requested character width makes Tk clip the left part of
            # the control in a narrow pane. Width 1 lets grid use the real space.
            box.configure(width=1)
            box.grid_configure(sticky="ew", padx=(0, 1))
            self._configure_bounded_combobox(box)

        if description_label is not None:
            description_label.grid_configure(row=6, column=0, columnspan=2, sticky="ew", pady=(7, 2))
        if notice_label is not None:
            notice_label.grid_configure(row=7, column=0, columnspan=2, sticky="ew", pady=(2, 0))

        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(7, 0))
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="添加 LUT…", command=self._add_user_lut).grid(
            row=0, column=0, sticky="ew", padx=(0, 3)
        )
        ttk.Button(actions, text="打开 LUT 文件夹", command=self._open_lut_directory).grid(
            row=0, column=1, sticky="ew", padx=(3, 0)
        )
        ttk.Label(
            frame,
            textvariable=self.lut_directory_text,
            foreground="#777",
            wraplength=300,
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(5, 0))

    def configure_bounded_combobox(self: Any, box: ttk.Combobox) -> None:
        box.configure(
            postcommand=lambda target=box: self.root.after_idle(
                lambda: self._resize_combobox_popup(target)
            )
        )

    def resize_combobox_popup(self: Any, box: ttk.Combobox) -> None:
        try:
            values = tuple(str(value) for value in box.cget("values"))
            if not values:
                return
            font = tkfont.nametofont("TkDefaultFont", root=self.root)
            longest = max(font.measure(value) for value in values)
            window_left = int(self.root.winfo_rootx())
            window_right = window_left + int(self.root.winfo_width())
            desired = max(int(box.winfo_width()), longest + 52)
            desired = min(desired, max(260, int(self.root.winfo_width()) - 32))
            popup = str(box.tk.call("ttk::combobox::PopdownWindow", str(box)))
            listbox = popup + ".f.l"
            average = max(7, font.measure("汉"))
            characters = max(20, int(math.ceil((desired - 36) / average)))
            box.tk.call(listbox, "configure", "-width", characters)
            x = min(int(box.winfo_rootx()), window_right - desired - 8)
            x = max(window_left + 8, x)
            y = int(box.winfo_rooty() + box.winfo_height())
            height = max(80, int(box.tk.call("winfo", "reqheight", popup)))
            box.tk.call("wm", "geometry", popup, f"{desired}x{height}+{x}+{y}")
        except (tk.TclError, TypeError, ValueError):
            # Some native Tk themes manage the popup themselves. The entry still
            # remains correctly sized and unclipped in those themes.
            return

    def rebuild_framed_preview_toolbar(self: Any) -> None:
        preview_panel = getattr(self, "preview_panel", None)
        if preview_panel is None:
            return
        viewbar = next(
            (
                child
                for child in preview_panel.winfo_children()
                if isinstance(child, ttk.Frame)
                and str(child.grid_info().get("row")) == "0"
            ),
            None,
        )
        if viewbar is None:
            return
        for child in viewbar.winfo_children():
            child.destroy()
        for column in range(6):
            viewbar.columnconfigure(column, weight=0)
        viewbar.columnconfigure(4, weight=1)

        crop_group = ttk.LabelFrame(viewbar, text="裁切工具", padding=(6, 3))
        crop_group.grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Radiobutton(
            crop_group,
            text="平移",
            value="pan",
            variable=self.interaction_mode,
            command=self._update_cursor,
        ).grid(row=0, column=0, padx=(0, 2))
        ttk.Radiobutton(
            crop_group,
            text="裁切",
            value="crop",
            variable=self.interaction_mode,
            command=self._update_cursor,
        ).grid(row=0, column=1, padx=2)
        ttk.Button(crop_group, text="重置裁切", command=self.reset_crop).grid(
            row=0, column=2, padx=(5, 0)
        )

        zoom_group = ttk.LabelFrame(viewbar, text="缩放", padding=(6, 3))
        zoom_group.grid(row=0, column=1, sticky="w", padx=(0, 6))
        ttk.Button(zoom_group, text="−", width=3, command=lambda: self.zoom_by(1 / 1.25)).grid(
            row=0, column=0, padx=(0, 2)
        )
        ttk.Button(zoom_group, text="+", width=3, command=lambda: self.zoom_by(1.25)).grid(
            row=0, column=1, padx=2
        )
        ttk.Button(zoom_group, text="适应", command=self.zoom_fit_view).grid(row=0, column=2, padx=2)
        ttk.Button(zoom_group, text="100%", command=self.zoom_actual).grid(row=0, column=3, padx=2)
        ttk.Button(zoom_group, text="200%", command=lambda: self.set_zoom(2.0)).grid(
            row=0, column=4, padx=(2, 4)
        )
        ttk.Label(zoom_group, textvariable=self.zoom_status).grid(row=0, column=5, padx=(5, 0))

        rotate_group = ttk.LabelFrame(viewbar, text="旋转", padding=(6, 3))
        rotate_group.grid(row=0, column=2, sticky="w", padx=(0, 6))
        ttk.Button(rotate_group, text="左转 90°", command=lambda: self.rotate_current(-90)).grid(
            row=0, column=0, padx=(0, 2)
        )
        ttk.Button(rotate_group, text="右转 90°", command=lambda: self.rotate_current(90)).grid(
            row=0, column=1, padx=2
        )
        ttk.Label(rotate_group, textvariable=self.rotation_status).grid(
            row=0, column=2, padx=(5, 0)
        )

        ttk.Label(viewbar, textvariable=self.crop_status, anchor="e").grid(
            row=0, column=5, sticky="e", padx=(8, 0)
        )
        self._v072_viewbar = viewbar
        self._v072_tool_groups = (crop_group, zoom_group, rotate_group)

    def rebuild_framed_geometry_toolbar(self: Any) -> None:
        preview_panel = getattr(self, "preview_panel", None)
        if preview_panel is None:
            return
        bar = next(
            (
                child
                for child in preview_panel.winfo_children()
                if isinstance(child, ttk.LabelFrame)
                and _widget_text(child) == "几何校正"
            ),
            None,
        )
        if bar is None:
            return
        for child in bar.winfo_children():
            child.destroy()
        for column in range(6):
            bar.columnconfigure(column, weight=0)
        bar.columnconfigure(4, weight=1)

        range_group = ttk.LabelFrame(bar, text="范围", padding=(5, 3))
        range_group.grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Button(range_group, text="自动范围", command=self.detect_frame_range).grid(row=0, column=0)

        straighten_group = ttk.LabelFrame(bar, text="拉直", padding=(5, 3))
        straighten_group.grid(row=0, column=1, sticky="w", padx=(0, 6))
        straighten = ttk.Spinbox(
            straighten_group,
            from_=-15.0,
            to=15.0,
            increment=0.1,
            textvariable=self.straighten_angle,
            width=7,
            justify="right",
        )
        straighten.grid(row=0, column=0, padx=(0, 2))
        straighten.bind("<Return>", lambda _event: self.commit_straighten())
        straighten.bind("<FocusOut>", lambda _event: self.commit_straighten())
        ttk.Label(straighten_group, text="°").grid(row=0, column=1, padx=(0, 4))
        ttk.Button(
            straighten_group,
            text="−0.1",
            width=5,
            command=lambda: self.adjust_straighten(-0.1),
        ).grid(row=0, column=2, padx=2)
        ttk.Button(
            straighten_group,
            text="+0.1",
            width=5,
            command=lambda: self.adjust_straighten(0.1),
        ).grid(row=0, column=3, padx=(2, 0))

        transform_group = ttk.LabelFrame(bar, text="变换", padding=(5, 3))
        transform_group.grid(row=0, column=2, sticky="w", padx=(0, 6))
        ttk.Button(
            transform_group,
            text="水平翻转",
            command=lambda: self.toggle_flip("horizontal"),
        ).grid(row=0, column=0, padx=(0, 2))
        ttk.Button(
            transform_group,
            text="垂直翻转",
            command=lambda: self.toggle_flip("vertical"),
        ).grid(row=0, column=1, padx=2)
        self.perspective_button = ttk.Button(
            transform_group,
            text="四角透视",
            command=self.toggle_perspective_mode,
        )
        self.perspective_button.grid(row=0, column=2, padx=2)
        ttk.Button(transform_group, text="重置几何", command=self.reset_geometry).grid(
            row=0, column=3, padx=(2, 0)
        )

        ttk.Label(bar, textvariable=self.geometry_status, anchor="e").grid(
            row=0, column=5, sticky="e", padx=(8, 0)
        )
        self._v072_geometry_bar = bar
        self._v072_geometry_groups = (range_group, straighten_group, transform_group)

    def add_project_folder_action(self: Any) -> None:
        header = getattr(self, "_compact_roll_header", None)
        if header is None:
            return
        button = ttk.Button(header, text="打开 project 文件夹", command=self._open_project_directory)
        button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        self.project_folder_button = button

    def refresh_user_lut_library(self: Any) -> None:
        directory = default_lut_directory()
        self.lut_directory_text.set(f"LUT 文件夹：{directory}")
        files = list_cube_luts(directory)
        label_to_file: dict[str, str] = {}
        file_to_label: dict[str, str] = {}
        for path in files:
            label = f"用户 LUT · {path.stem}"
            if label in label_to_file:
                label = f"用户 LUT · {path.name}"
            label_to_file[label] = path.name
            file_to_label[path.name] = label
        self._user_lut_label_to_file = label_to_file
        self._user_lut_file_to_label = file_to_label

        built_in = tuple(str(FILM_PROFILES[key]["label"]) for key in FILM_PROFILE_ORDER)
        if self.film_profile_box is not None:
            self.film_profile_box.configure(values=built_in + tuple(label_to_file.keys()))
        filename = safe_lut_filename(self.user_lut_file.get())
        if filename:
            self.film_profile_label.set(file_to_label.get(filename, f"用户 LUT（缺失）· {filename}"))
        self._update_style_library_text()

    def add_user_lut(self: Any) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="添加用户 LUT",
            filetypes=(("Cube LUT", "*.cube"), ("所有文件", "*.*")),
        )
        if not selected:
            return
        source = Path(selected)
        try:
            parsed = load_cube_lut(source)
        except (OSError, UnicodeError, ValueError) as exc:
            messagebox.showerror("LUT 无效", str(exc), parent=self.root)
            return

        directory = default_lut_directory()
        destination = directory / source.name
        if destination.exists() and destination.resolve(strict=False) != source.resolve(strict=False):
            replace = messagebox.askyesno(
                "LUT 已存在",
                f"{destination.name} 已存在，是否替换？",
                parent=self.root,
            )
            if not replace:
                return
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if destination.resolve(strict=False) != source.resolve(strict=False):
                shutil.copy2(source, destination)
        except OSError as exc:
            messagebox.showerror("复制 LUT 失败", str(exc), parent=self.root)
            return

        self.user_lut_file.set(destination.name)
        self.profile.set("generic")
        self._refresh_user_lut_library()
        self._control_changed()
        self.status.set(
            f"已添加用户 LUT：{parsed.title}（{parsed.size}{'³' if parsed.dimension == 3 else ' 点'}）。"
        )

    def open_lut_directory(self: Any) -> None:
        try:
            _open_directory(default_lut_directory())
        except OSError as exc:
            messagebox.showerror("无法打开 LUT 文件夹", str(exc), parent=self.root)

    def open_project_directory(self: Any) -> None:
        try:
            _open_directory(default_project_directory())
        except OSError as exc:
            messagebox.showerror("无法打开 project 文件夹", str(exc), parent=self.root)

    def style_selected(self: Any, kind: str) -> None:
        if kind != "film":
            original_style_selected(self, kind)
            return
        label = self.film_profile_label.get()
        filename = self._user_lut_label_to_file.get(label)
        if filename:
            self.user_lut_file.set(filename)
            self.profile.set("generic")
            self._update_style_library_text()
            self._control_changed()
            return
        self.user_lut_file.set("")
        original_style_selected(self, kind)

    def update_style_library_text(self: Any) -> None:
        original_update_style_library_text(self)
        filename = safe_lut_filename(self.user_lut_file.get())
        if not filename:
            return
        scanner_key = canonical_scanner_profile(self.scanner_profile.get())
        scanner_description = str(SCANNER_PROFILES[scanner_key]["description"])
        path = resolve_user_lut(default_lut_directory(), filename)
        if path is None or not path.is_file():
            self.film_profile_label.set(f"用户 LUT（缺失）· {filename}")
            lut_description = f"项目指定了 {filename}，但 LUT 文件夹中没有该文件。"
        else:
            self.film_profile_label.set(
                self._user_lut_file_to_label.get(filename, f"用户 LUT · {path.stem}")
            )
            try:
                parsed = load_cube_lut(path)
                dimension = f"{parsed.size}³ 3D" if parsed.dimension == 3 else f"{parsed.size} 点 1D"
                lut_description = f"{parsed.title}，{dimension} Cube LUT，使用胶卷强度控制混合比例。"
            except (OSError, UnicodeError, ValueError) as exc:
                lut_description = f"{filename} 无法读取：{exc}"
        self.style_description.set(f"扫描：{scanner_description}\n胶卷：{lut_description}")

    def controls_value(self: Any) -> Controls:
        controls = original_controls_value(self)
        controls.user_lut = safe_lut_filename(self.user_lut_file.get())
        if controls.user_lut:
            controls.profile = "generic"
        return controls.sanitized()

    def apply_controls(self: Any, controls: Controls) -> None:
        original_apply_controls(self, controls)
        self.user_lut_file.set(safe_lut_filename(getattr(controls, "user_lut", "")))
        self._refresh_user_lut_library()

    app_class._build_variables = build_variables
    app_class._build_ui = build_ui
    app_class._configure_style_selector_layout = configure_style_selector_layout
    app_class._configure_bounded_combobox = configure_bounded_combobox
    app_class._resize_combobox_popup = resize_combobox_popup
    app_class._rebuild_framed_preview_toolbar = rebuild_framed_preview_toolbar
    app_class._rebuild_framed_geometry_toolbar = rebuild_framed_geometry_toolbar
    app_class._add_project_folder_action = add_project_folder_action
    app_class._refresh_user_lut_library = refresh_user_lut_library
    app_class._add_user_lut = add_user_lut
    app_class._open_lut_directory = open_lut_directory
    app_class._open_project_directory = open_project_directory
    app_class._style_selected = style_selected
    app_class._update_style_library_text = update_style_library_text
    app_class.controls_value = controls_value
    app_class.apply_controls = apply_controls
    app_class._v072_workspace_lut_layout_applied = True

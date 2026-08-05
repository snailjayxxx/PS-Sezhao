from __future__ import annotations

import sys
from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


MACOS_FONT_CANDIDATES = (
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    ".AppleSystemUIFont",
    "Arial Unicode MS",
)
WINDOWS_FONT_CANDIDATES = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "Segoe UI",
)
LINUX_FONT_CANDIDATES = (
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "WenQuanYi Micro Hei",
    "DejaVu Sans",
)


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def _widget_text(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("text"))
    except (AttributeError, tk.TclError):
        return ""


def _widget_textvariable(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("textvariable"))
    except (AttributeError, tk.TclError):
        return ""


def choose_cjk_ui_family(root: tk.Misc) -> str | None:
    """Choose a platform-native UI family that contains Chinese glyphs."""

    try:
        available = set(tkfont.families(root))
    except tk.TclError:
        return None
    if sys.platform == "darwin":
        candidates = MACOS_FONT_CANDIDATES
    elif sys.platform.startswith("win"):
        candidates = WINDOWS_FONT_CANDIDATES
    else:
        candidates = LINUX_FONT_CANDIDATES
    return next((family for family in candidates if family in available), None)


def apply_v071_text_layout_patch(app_class: Type[Any]) -> None:
    """Prevent CJK clipping and cross-pane toolbar drawing on desktop builds."""

    if getattr(app_class, "_v071_text_layout_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        self._configure_cjk_typography()
        original_build_ui(self)
        self._configure_compact_toolbar_layouts()

    def configure_cjk_typography(self: Any) -> None:
        family = choose_cjk_ui_family(self.root)
        if family:
            for name in (
                "TkDefaultFont",
                "TkTextFont",
                "TkMenuFont",
                "TkHeadingFont",
                "TkCaptionFont",
                "TkSmallCaptionFont",
                "TkIconFont",
                "TkTooltipFont",
            ):
                try:
                    tkfont.nametofont(name, root=self.root).configure(family=family)
                except tk.TclError:
                    continue
        try:
            default_font = tkfont.nametofont("TkDefaultFont", root=self.root)
            line_height = int(default_font.metrics("linespace"))
            style = ttk.Style(self.root)
            style.configure("Treeview", rowheight=max(24, line_height + 8))
            style.configure("TButton", padding=(7, 4))
            style.configure("TCheckbutton", padding=(2, 3))
            style.configure("TRadiobutton", padding=(2, 3))
        except tk.TclError:
            pass
        self._ps_sezhao_ui_font_family = family or ""

    def configure_compact_toolbar_layouts(self: Any) -> None:
        self._reflow_global_toolbar()
        self._reflow_preview_toolbar()
        self._reflow_geometry_toolbar()
        self._reflow_roll_project_header()
        self.root.after_idle(self._refresh_compact_text_wraps)

    def reflow_global_toolbar(self: Any) -> None:
        toolbar = next(
            (
                child
                for child in self.root.winfo_children()
                if isinstance(child, ttk.Frame)
                and str(child.grid_info().get("row")) == "0"
            ),
            None,
        )
        if toolbar is None:
            return

        for column in range(18):
            toolbar.columnconfigure(column, weight=0)
        toolbar.columnconfigure(9, weight=1)

        button_positions = {
            "添加图像": (0, 0),
            "添加文件夹": (0, 1),
            "移除选中": (0, 2),
            "上一张": (0, 4),
            "下一张": (0, 5),
            "自动分析边框": (0, 6),
            "↶ 撤销": (1, 0),
            "↷ 重做": (1, 1),
            "吸管：胶片基底": (1, 3),
            "吸管：中性色": (1, 4),
            "恢复默认": (1, 8),
        }
        for widget in toolbar.winfo_children():
            text = _widget_text(widget)
            if text in button_positions:
                row, column = button_positions[text]
                widget.grid_configure(
                    row=row,
                    column=column,
                    columnspan=1,
                    sticky="ew" if text in {"↶ 撤销", "↷ 重做"} else "",
                    padx=3,
                    pady=(4, 0) if row else 0,
                )
                continue
            if isinstance(widget, ttk.Separator):
                try:
                    old_column = int(widget.grid_info().get("column", -1))
                except (TypeError, ValueError):
                    old_column = -1
                if old_column <= 3:
                    widget.grid_configure(row=0, column=3, sticky="ns", padx=6, pady=0)
                else:
                    widget.grid_configure(row=0, column=8, sticky="ns", padx=6, pady=0)
                continue
            if isinstance(widget, ttk.Combobox):
                try:
                    if str(widget.cget("textvariable")) == str(self.sample_size):
                        widget.grid_configure(row=1, column=6, padx=0, pady=(4, 0))
                except tk.TclError:
                    pass
                continue
            if isinstance(widget, ttk.Checkbutton) and text == "自动预览":
                widget.grid_configure(row=1, column=7, sticky="w", padx=8, pady=(4, 0))
                continue
            if isinstance(widget, ttk.Label):
                variable = _widget_textvariable(widget)
                if variable == str(self.status):
                    widget.grid_configure(row=0, column=9, sticky="ew", padx=(8, 3), pady=0)
                elif text == "取样":
                    widget.grid_configure(row=1, column=5, padx=(10, 3), pady=(4, 0))
                elif text.startswith("Ctrl/Cmd+Z"):
                    widget.grid_configure(row=1, column=2, columnspan=1, sticky="w", padx=(8, 6), pady=(4, 0))

    def reflow_preview_toolbar(self: Any) -> None:
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

        for column in range(18):
            viewbar.columnconfigure(column, weight=0)
        viewbar.columnconfigure(10, weight=1)

        for widget in viewbar.winfo_children():
            text = _widget_text(widget)
            variable = _widget_textvariable(widget)
            if text == "左转 90°":
                widget.grid_configure(row=1, column=0, padx=(0, 3), pady=(4, 0))
            elif text == "右转 90°":
                widget.grid_configure(row=1, column=1, padx=3, pady=(4, 0))
            elif variable == str(getattr(self, "rotation_status", "")):
                widget.grid_configure(row=1, column=2, sticky="w", padx=(6, 3), pady=(4, 0))
            elif variable == str(self.crop_status):
                widget.grid_configure(
                    row=1,
                    column=3,
                    columnspan=8,
                    sticky="e",
                    padx=(8, 0),
                    pady=(4, 0),
                )
            elif variable == str(self.zoom_status):
                widget.grid_configure(sticky="e")
            elif isinstance(widget, ttk.Separator):
                try:
                    old_column = int(widget.grid_info().get("column", -1))
                except (TypeError, ValueError):
                    old_column = -1
                if old_column >= 11:
                    widget.grid_remove()
        self._compact_preview_toolbar = viewbar

    def reflow_geometry_toolbar(self: Any) -> None:
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

        for column in range(14):
            bar.columnconfigure(column, weight=0)
        bar.columnconfigure(4, weight=1)

        positions = {
            "水平翻转": (1, 0),
            "垂直翻转": (1, 1),
            "四角透视": (1, 2),
            "取消四角": (1, 2),
            "重置几何": (1, 3),
        }
        for widget in bar.winfo_children():
            text = _widget_text(widget)
            variable = _widget_textvariable(widget)
            if text in positions:
                row, column = positions[text]
                widget.grid_configure(row=row, column=column, padx=2, pady=(4, 0))
            elif variable == str(getattr(self, "geometry_status", "")):
                widget.grid_configure(
                    row=1,
                    column=4,
                    columnspan=2,
                    sticky="e",
                    padx=(8, 0),
                    pady=(4, 0),
                )
        self._compact_geometry_toolbar = bar

    def reflow_roll_project_header(self: Any) -> None:
        list_panel = getattr(self, "list_panel", None)
        if list_panel is None:
            return
        header = next(
            (
                child
                for child in list_panel.winfo_children()
                if isinstance(child, ttk.LabelFrame)
                and _widget_text(child) == "胶卷项目"
            ),
            None,
        )
        if header is None:
            return

        for column in range(4):
            header.columnconfigure(column, weight=0)
        header.columnconfigure((0, 1), weight=1)

        title_label = None
        summary_label = None
        for widget in header.winfo_children():
            variable = _widget_textvariable(widget)
            if variable == str(getattr(self, "active_roll_title", "")):
                title_label = widget
            elif variable == str(getattr(self, "active_roll_summary", "")):
                summary_label = widget
        if title_label is not None:
            title_label.grid_configure(row=0, column=0, columnspan=2, sticky="w")
        if summary_label is not None:
            summary_label.grid_configure(row=1, column=0, columnspan=2, sticky="w", pady=(2, 5))
            self._roll_summary_label = summary_label

        buttons = (
            (getattr(self, "roll_new_button", None), 2, 0),
            (getattr(self, "roll_open_button", None), 2, 1),
            (getattr(self, "roll_settings_button", None), 3, 0),
            (getattr(self, "output_presets_button", None), 3, 1),
        )
        for button, row, column in buttons:
            if button is not None:
                button.grid_configure(
                    row=row,
                    column=column,
                    sticky="ew",
                    padx=(0, 3) if column == 0 else (3, 0),
                    pady=(4, 0) if row == 3 else 0,
                )
        header.bind("<Configure>", self._resize_roll_summary_wrap, add="+")
        self._compact_roll_header = header

    def resize_roll_summary_wrap(self: Any, event: tk.Event | None = None) -> None:
        label = getattr(self, "_roll_summary_label", None)
        header = getattr(self, "_compact_roll_header", None)
        if label is None or header is None:
            return
        width = int(getattr(event, "width", 0) or header.winfo_width() or 1)
        try:
            label.configure(wraplength=max(120, width - 20))
        except tk.TclError:
            pass

    def refresh_compact_text_wraps(self: Any) -> None:
        self._resize_roll_summary_wrap()
        for bar_name in ("_compact_preview_toolbar", "_compact_geometry_toolbar"):
            bar = getattr(self, bar_name, None)
            if bar is None:
                continue
            try:
                bar.update_idletasks()
            except tk.TclError:
                continue

    app_class._build_ui = build_ui
    app_class._configure_cjk_typography = configure_cjk_typography
    app_class._configure_compact_toolbar_layouts = configure_compact_toolbar_layouts
    app_class._reflow_global_toolbar = reflow_global_toolbar
    app_class._reflow_preview_toolbar = reflow_preview_toolbar
    app_class._reflow_geometry_toolbar = reflow_geometry_toolbar
    app_class._reflow_roll_project_header = reflow_roll_project_header
    app_class._resize_roll_summary_wrap = resize_roll_summary_wrap
    app_class._refresh_compact_text_wraps = refresh_compact_text_wraps
    app_class._v071_text_layout_applied = True

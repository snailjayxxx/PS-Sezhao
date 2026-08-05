from __future__ import annotations

from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import ttk


LIST_MIN_WIDTH = 160
PREVIEW_MIN_WIDTH = 360
CONTROLS_MIN_WIDTH = 280
SASH_WIDTH = 8


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def initial_sash_positions(total_width: int) -> tuple[int, int]:
    """Return useful first-run sash positions while preserving all pane minima."""

    width = max(
        int(total_width),
        LIST_MIN_WIDTH + PREVIEW_MIN_WIDTH + CONTROLS_MIN_WIDTH + SASH_WIDTH * 2,
    )
    left = min(320, max(220, round(width * 0.18)))
    controls_width = min(520, max(340, round(width * 0.24)))
    right = width - controls_width

    if right - left < PREVIEW_MIN_WIDTH:
        shortage = PREVIEW_MIN_WIDTH - (right - left)
        left = max(LIST_MIN_WIDTH, left - shortage // 2)
        right = min(width - CONTROLS_MIN_WIDTH, right + shortage - shortage // 2)
    return int(left), int(right)


def apply_v061_resizable_layout_patch(app_class: Type[Any]) -> None:
    """Replace the subtle fixed-width layout with three clearly resizable panes."""

    if getattr(app_class, "_v061_resizable_layout_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._replace_main_three_pane_layout()

    def replace_main_three_pane_layout(self: Any) -> None:
        old_body = next(
            (
                child
                for child in self.root.winfo_children()
                if isinstance(child, ttk.Panedwindow)
            ),
            None,
        )
        if old_body is None:
            return

        old_body.destroy()
        body = tk.PanedWindow(
            self.root,
            orient=tk.HORIZONTAL,
            borderwidth=0,
            relief=tk.FLAT,
            sashwidth=SASH_WIDTH,
            sashpad=2,
            sashrelief=tk.RAISED,
            showhandle=True,
            handlesize=10,
            handlepad=22,
            opaqueresize=True,
            background="#b8b8b8",
        )
        body.grid(row=1, column=0, sticky="nsew")

        list_panel = ttk.Frame(body, padding=(8, 8, 4, 8))
        preview_frame = ttk.Frame(body, padding=8)
        controls_outer = ttk.Frame(body, padding=(4, 8, 8, 8))
        body.add(
            list_panel,
            minsize=LIST_MIN_WIDTH,
            stretch="always",
            sticky="nsew",
        )
        body.add(
            preview_frame,
            minsize=PREVIEW_MIN_WIDTH,
            stretch="always",
            sticky="nsew",
        )
        body.add(
            controls_outer,
            minsize=CONTROLS_MIN_WIDTH,
            stretch="always",
            sticky="nsew",
        )

        self.main_panedwindow = body
        self.list_panel = list_panel
        self.preview_panel = preview_frame
        self.controls_outer = controls_outer
        self._pane_layout_initialized = False

        self._build_file_panel(list_panel)
        self._build_preview_panel(preview_frame)
        self._build_controls_panel(controls_outer)

        # v0.5.4 added these panels after _build_ui rather than inside
        # _build_controls_panel. The old widgets were destroyed with the old
        # panes, so recreate/configure them for the new controls container.
        if hasattr(self, "_expand_base_adjust_controls"):
            self._expand_base_adjust_controls()
        if hasattr(self, "_configure_direct_base_panel"):
            self._configure_direct_base_panel()
        if hasattr(self, "_add_neutral_gain_panel"):
            self._add_neutral_gain_panel()

        self._make_controls_panel_responsive()

        # The earlier patches installed wheel and drop bindings on the widgets
        # that were just replaced. Reinstall them on the new pane widgets.
        if hasattr(self, "_install_side_panel_wheel_scrolling"):
            self._install_side_panel_wheel_scrolling()
        if hasattr(self, "_install_drop_targets"):
            self._install_drop_targets()
        if hasattr(self, "_update_history_buttons"):
            self._update_history_buttons()

        self.root.after_idle(self._set_initial_pane_sashes)

    def make_controls_panel_responsive(self: Any) -> None:
        controls_canvas = self.controls.master
        if not isinstance(controls_canvas, tk.Canvas):
            return

        window_items = [
            item
            for item in controls_canvas.find_all()
            if controls_canvas.type(item) == "window"
        ]
        if not window_items:
            return

        self.controls_canvas = controls_canvas
        self.controls_window_item = window_items[0]
        self.controls.columnconfigure(0, weight=1)

        # Remove the old 340 px canvas request. The enclosing pane now decides
        # the width, and the embedded frame follows the canvas on every resize.
        controls_canvas.configure(width=1)
        controls_canvas.bind(
            "<Configure>",
            self._resize_controls_content,
            add="+",
        )
        self._resize_controls_content()

    def resize_controls_content(self: Any, event: tk.Event | None = None) -> None:
        canvas = getattr(self, "controls_canvas", None)
        window_item = getattr(self, "controls_window_item", None)
        if canvas is None or window_item is None:
            return

        width = int(getattr(event, "width", 0) or canvas.winfo_width() or 1)
        width = max(1, width)
        canvas.itemconfigure(window_item, width=width)

        wraplength = max(180, width - 28)
        for widget in _walk_widgets(self.controls):
            if not isinstance(widget, ttk.Label):
                continue
            try:
                current = float(widget.cget("wraplength") or 0)
            except (TypeError, ValueError, tk.TclError):
                continue
            if current > 0:
                widget.configure(wraplength=wraplength)

        bounds = canvas.bbox("all")
        if bounds is not None:
            canvas.configure(scrollregion=bounds)

    def set_initial_pane_sashes(self: Any) -> None:
        if getattr(self, "_pane_layout_initialized", False):
            return
        body = getattr(self, "main_panedwindow", None)
        if body is None:
            return

        body.update_idletasks()
        width = int(body.winfo_width())
        if width < 800:
            self.root.after(50, self._set_initial_pane_sashes)
            return

        left, right = initial_sash_positions(width)
        body.sash_place(0, left, 0)
        body.sash_place(1, right, 0)
        self._pane_layout_initialized = True

    app_class._build_ui = build_ui
    app_class._replace_main_three_pane_layout = replace_main_three_pane_layout
    app_class._make_controls_panel_responsive = make_controls_panel_responsive
    app_class._resize_controls_content = resize_controls_content
    app_class._set_initial_pane_sashes = set_initial_pane_sashes
    app_class._v061_resizable_layout_applied = True

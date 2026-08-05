from __future__ import annotations

from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import ttk


LIST_MIN_WIDTH = 160
PREVIEW_MIN_WIDTH = 360
CONTROLS_MIN_WIDTH = 280
SASH_WIDTH = 10


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def initial_sash_positions(total_width: int) -> tuple[int, int]:
    """Return useful first-run sash positions while preserving pane minima."""

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


def clamp_sash_positions(total_width: int, left: int, right: int) -> tuple[int, int]:
    """Clamp user-dragged sashes without fixing the three pane proportions."""

    width = max(
        int(total_width),
        LIST_MIN_WIDTH + PREVIEW_MIN_WIDTH + CONTROLS_MIN_WIDTH,
    )
    max_left = width - PREVIEW_MIN_WIDTH - CONTROLS_MIN_WIDTH
    left = min(max_left, max(LIST_MIN_WIDTH, int(left)))
    min_right = left + PREVIEW_MIN_WIDTH
    max_right = width - CONTROLS_MIN_WIDTH
    right = min(max_right, max(min_right, int(right)))
    return left, right


def apply_v061_resizable_layout_patch(app_class: Type[Any]) -> None:
    """Make the existing three panes resizable without destroying any widgets.

    v0.6.1 initially rebuilt the complete body after all older UI patches had
    already stored references to RAW white-balance entries and other controls.
    Destroying that body invalidated those references and caused a startup
    TclError. This implementation keeps the original widgets alive, enhances
    the existing ttk.Panedwindow and only makes the embedded controls frame
    follow the current right-pane width.
    """

    if getattr(app_class, "_v061_resizable_layout_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._configure_existing_three_pane_layout()

    def configure_existing_three_pane_layout(self: Any) -> None:
        body = next(
            (
                child
                for child in self.root.winfo_children()
                if isinstance(child, ttk.Panedwindow)
            ),
            None,
        )
        if body is None:
            return

        panes = tuple(body.panes())
        if len(panes) != 3:
            return

        self.main_panedwindow = body
        self.list_panel = body.nametowidget(str(panes[0]))
        self.preview_panel = body.nametowidget(str(panes[1]))
        self.controls_outer = body.nametowidget(str(panes[2]))
        self._pane_layout_initialized = False
        self._pane_constraint_after = None

        # Preserve the original controls and their Python references. Only
        # adjust pane weights and style so the two dividers remain draggable.
        for pane, weight in zip(panes, (1, 5, 2)):
            try:
                body.pane(pane, weight=weight)
            except tk.TclError:
                pass

        try:
            style_name = "PSSezhao.TPanedwindow"
            style = ttk.Style(self.root)
            style.configure(style_name, sashwidth=SASH_WIDTH, sashrelief=tk.RAISED)
            body.configure(style=style_name)
        except tk.TclError:
            pass

        self._make_controls_panel_responsive()
        body.bind("<ButtonRelease-1>", self._schedule_pane_constraints, add="+")
        body.bind("<Configure>", self._schedule_pane_constraints, add="+")
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

        # Remove the old 340 px canvas request. The existing right pane now
        # decides the width and the embedded controls frame follows it live.
        controls_canvas.configure(width=1)
        controls_canvas.bind("<Configure>", self._resize_controls_content, add="+")
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

    def schedule_pane_constraints(self: Any, _event: tk.Event | None = None) -> None:
        pending = getattr(self, "_pane_constraint_after", None)
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except tk.TclError:
                pass
        self._pane_constraint_after = self.root.after_idle(self._constrain_pane_sashes)

    def constrain_pane_sashes(self: Any) -> None:
        self._pane_constraint_after = None
        body = getattr(self, "main_panedwindow", None)
        if body is None or not getattr(self, "_pane_layout_initialized", False):
            return

        width = int(body.winfo_width())
        if width < LIST_MIN_WIDTH + PREVIEW_MIN_WIDTH + CONTROLS_MIN_WIDTH:
            return
        try:
            left = int(body.sashpos(0))
            right = int(body.sashpos(1))
            safe_left, safe_right = clamp_sash_positions(width, left, right)
            if safe_left != left:
                body.sashpos(0, safe_left)
            if safe_right != right:
                body.sashpos(1, safe_right)
        except tk.TclError:
            return

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
        try:
            body.sashpos(0, left)
            body.sashpos(1, right)
        except tk.TclError:
            return
        self._pane_layout_initialized = True
        self._schedule_pane_constraints()

    app_class._build_ui = build_ui
    app_class._configure_existing_three_pane_layout = configure_existing_three_pane_layout
    app_class._make_controls_panel_responsive = make_controls_panel_responsive
    app_class._resize_controls_content = resize_controls_content
    app_class._schedule_pane_constraints = schedule_pane_constraints
    app_class._constrain_pane_sashes = constrain_pane_sashes
    app_class._set_initial_pane_sashes = set_initial_pane_sashes
    app_class._v061_resizable_layout_applied = True

from __future__ import annotations

from typing import Any, Callable, Iterator, Type

import tkinter as tk
from tkinter import ttk


WheelHandler = Callable[[tk.Event, int | None], str]
BASE_MIN_UNITS = -255
BASE_MAX_UNITS = 255


def _wheel_units(event: tk.Event, direction: int | None = None) -> int:
    """Return Tk yview units for Windows/macOS and X11 wheel events."""

    if direction is not None:
        return -1 if direction > 0 else 1

    delta = float(getattr(event, "delta", 0) or 0)
    if delta == 0:
        return 0

    # Windows normally reports ±120. macOS trackpads usually report smaller
    # values, so preserve a little acceleration without making them jumpy.
    magnitude = abs(delta) / 120.0 if abs(delta) >= 120 else abs(delta)
    magnitude = max(1, min(6, round(magnitude)))
    return -magnitude if delta > 0 else magnitude


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def _bind_wheel(widget: tk.Misc, handler: WheelHandler) -> None:
    widget.bind("<MouseWheel>", lambda event: handler(event, None), add="+")
    widget.bind("<Button-4>", lambda event: handler(event, 1), add="+")
    widget.bind("<Button-5>", lambda event: handler(event, -1), add="+")


def apply_scroll_patch(app_class: Type[Any]) -> None:
    """Add v0.5.3 larger base adjustment and pointer-local panel scrolling."""

    if getattr(app_class, "_v053_scroll_patch_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._expand_base_adjust_controls()
        self._install_side_panel_wheel_scrolling()

    def expand_base_adjust_controls(self: Any) -> None:
        variable_names = {str(variable) for variable in self.base_adjust_units.values()}
        for widget in _walk_widgets(self.controls):
            if isinstance(widget, tk.Scale) and str(widget.cget("variable")) in variable_names:
                widget.configure(from_=BASE_MIN_UNITS, to=BASE_MAX_UNITS, resolution=1)
            elif isinstance(widget, ttk.LabelFrame):
                try:
                    if str(widget.cget("text")).startswith("胶片基底手动微调"):
                        widget.configure(text="胶片基底手动微调 · v0.5.3")
                except tk.TclError:
                    pass

    def commit_base_entry(self: Any, channel: str) -> str:
        try:
            value = float(self.base_adjust_entries[channel].get().strip())
        except (TypeError, ValueError):
            value = float(self.base_adjust_units[channel].get())
        value = round(min(BASE_MAX_UNITS, max(BASE_MIN_UNITS, value)))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()
        return "break"

    def adjust_base(self: Any, channel: str, direction: int) -> str:
        value = round(float(self.base_adjust_units[channel].get()) + int(direction))
        value = min(BASE_MAX_UNITS, max(BASE_MIN_UNITS, value))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()
        return "break"

    def scroll_controls(self: Any, event: tk.Event, direction: int | None = None) -> str:
        units = _wheel_units(event, direction)
        if units:
            self.controls.master.yview_scroll(units, "units")
        return "break"

    def scroll_file_list(self: Any, event: tk.Event, direction: int | None = None) -> str:
        units = _wheel_units(event, direction)
        if units:
            self.file_tree.yview_scroll(units, "units")
        return "break"

    def install_side_panel_wheel_scrolling(self: Any) -> None:
        controls_canvas = self.controls.master
        for widget in _walk_widgets(controls_canvas):
            _bind_wheel(widget, self._scroll_controls_wheel)

        # Let the entire left panel scroll the file list, not only the narrow
        # Treeview text area. This is especially helpful on Windows touchpads.
        file_panel = self.file_tree.master
        for widget in _walk_widgets(file_panel):
            _bind_wheel(widget, self._scroll_file_list_wheel)

    app_class._build_ui = build_ui
    app_class._expand_base_adjust_controls = expand_base_adjust_controls
    app_class.commit_base_entry = commit_base_entry
    app_class.adjust_base = adjust_base
    app_class._scroll_controls_wheel = scroll_controls
    app_class._scroll_file_list_wheel = scroll_file_list
    app_class._install_side_panel_wheel_scrolling = install_side_panel_wheel_scrolling
    app_class._v053_scroll_patch_applied = True

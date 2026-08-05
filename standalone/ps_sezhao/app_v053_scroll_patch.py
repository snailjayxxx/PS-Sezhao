from __future__ import annotations

from typing import Any, Callable, Iterator, Type

import tkinter as tk


WheelHandler = Callable[[tk.Event, int | None], str]


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
    """Add v0.5.3 pointer-local scrolling for the side panels."""

    if getattr(app_class, "_v053_scroll_patch_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._install_side_panel_wheel_scrolling()

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
    app_class._scroll_controls_wheel = scroll_controls
    app_class._scroll_file_list_wheel = scroll_file_list
    app_class._install_side_panel_wheel_scrolling = install_side_panel_wheel_scrolling
    app_class._v053_scroll_patch_applied = True

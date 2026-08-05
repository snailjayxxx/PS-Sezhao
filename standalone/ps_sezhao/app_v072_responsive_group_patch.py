from __future__ import annotations

from typing import Any, Type

import tkinter as tk
from tkinter import ttk


PREVIEW_WRAP_WIDTH = 900
GEOMETRY_WRAP_WIDTH = 820


def _textvariable(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("textvariable"))
    except (AttributeError, tk.TclError):
        return ""


def apply_v072_responsive_group_patch(app_class: Type[Any]) -> None:
    """Keep each framed tool group compact and wrap whole groups when needed."""

    if getattr(app_class, "_v072_responsive_group_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._finalize_v072_group_reflow()

    def finalize_group_reflow(self: Any) -> None:
        frame = getattr(self, "style_library_frame", None)
        if frame is not None:
            try:
                frame.configure(text="扫描仪与胶卷风格")
            except tk.TclError:
                pass

        for box in (
            getattr(self, "scanner_profile_box", None),
            getattr(self, "film_profile_box", None),
        ):
            if box is not None:
                box.configure(postcommand=lambda target=box: self._prepare_v072_combobox_popup(target))

        viewbar = getattr(self, "_v072_viewbar", None)
        if viewbar is not None:
            self._v072_crop_status_label = next(
                (
                    widget
                    for widget in viewbar.winfo_children()
                    if isinstance(widget, ttk.Label)
                    and _textvariable(widget) == str(self.crop_status)
                ),
                None,
            )
            viewbar.bind("<Configure>", self._layout_v072_preview_groups, add="+")

        geometry_bar = getattr(self, "_v072_geometry_bar", None)
        if geometry_bar is not None:
            self._v072_geometry_status_label = next(
                (
                    widget
                    for widget in geometry_bar.winfo_children()
                    if isinstance(widget, ttk.Label)
                    and _textvariable(widget) == str(self.geometry_status)
                ),
                None,
            )
            geometry_bar.bind("<Configure>", self._layout_v072_geometry_groups, add="+")

        self.root.after_idle(self._layout_v072_preview_groups)
        self.root.after_idle(self._layout_v072_geometry_groups)

    def prepare_combobox_popup(self: Any, box: ttk.Combobox) -> None:
        if box is getattr(self, "film_profile_box", None):
            self._refresh_user_lut_library()
        self.root.after_idle(lambda target=box: self._resize_combobox_popup(target))

    def layout_preview_groups(self: Any, event: tk.Event | None = None) -> None:
        viewbar = getattr(self, "_v072_viewbar", None)
        groups = getattr(self, "_v072_tool_groups", ())
        if viewbar is None or len(groups) != 3:
            return
        width = int(getattr(event, "width", 0) or viewbar.winfo_width() or 1)
        crop_group, zoom_group, rotate_group = groups
        crop_group.grid_configure(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 0))
        zoom_group.grid_configure(row=0, column=1, sticky="w", padx=(0, 6), pady=(0, 0))
        compact = width < PREVIEW_WRAP_WIDTH
        rotate_group.grid_configure(
            row=1 if compact else 0,
            column=0 if compact else 2,
            sticky="w",
            padx=(0, 6),
            pady=(5, 0) if compact else (0, 0),
        )
        status = getattr(self, "_v072_crop_status_label", None)
        if status is not None:
            status.grid_configure(
                row=1 if compact else 0,
                column=5,
                sticky="e",
                padx=(8, 0),
                pady=(5, 0) if compact else (0, 0),
            )

    def layout_geometry_groups(self: Any, event: tk.Event | None = None) -> None:
        bar = getattr(self, "_v072_geometry_bar", None)
        groups = getattr(self, "_v072_geometry_groups", ())
        if bar is None or len(groups) != 3:
            return
        width = int(getattr(event, "width", 0) or bar.winfo_width() or 1)
        range_group, straighten_group, transform_group = groups
        range_group.grid_configure(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 0))
        straighten_group.grid_configure(row=0, column=1, sticky="w", padx=(0, 6), pady=(0, 0))
        compact = width < GEOMETRY_WRAP_WIDTH
        transform_group.grid_configure(
            row=1 if compact else 0,
            column=0 if compact else 2,
            sticky="w",
            padx=(0, 6),
            pady=(5, 0) if compact else (0, 0),
        )
        status = getattr(self, "_v072_geometry_status_label", None)
        if status is not None:
            status.grid_configure(
                row=1 if compact else 0,
                column=5,
                sticky="e",
                padx=(8, 0),
                pady=(5, 0) if compact else (0, 0),
            )

    app_class._build_ui = build_ui
    app_class._finalize_v072_group_reflow = finalize_group_reflow
    app_class._prepare_v072_combobox_popup = prepare_combobox_popup
    app_class._layout_v072_preview_groups = layout_preview_groups
    app_class._layout_v072_geometry_groups = layout_geometry_groups
    app_class._v072_responsive_group_applied = True

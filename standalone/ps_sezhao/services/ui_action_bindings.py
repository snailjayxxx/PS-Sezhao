from __future__ import annotations

from typing import Any, Type

import tkinter as tk
from tkinter import messagebox, ttk


def apply_ui_action_bindings(app_class: Type[Any]) -> None:
    """Bind the visible crop and geometry controls after all services are installed."""

    if getattr(app_class, "_ui_action_bindings_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._restore_crop_geometry_controls()

    def report_action_error(self: Any, title: str, error: Exception) -> None:
        message = str(error) or error.__class__.__name__
        try:
            self.status.set(f"{title}失败：{message}")
        except (AttributeError, tk.TclError):
            pass
        messagebox.showerror(f"{title}失败", message, parent=self.root)

    def invoke_crop_editing(self: Any) -> None:
        try:
            self.toggle_crop_editing()
        except Exception as error:
            self._report_ui_action_error("裁切", error)

    def invoke_rotation(self: Any, clockwise_degrees: int) -> None:
        try:
            self.rotate_current(clockwise_degrees)
        except Exception as error:
            self._report_ui_action_error("旋转", error)

    def invoke_flip(self: Any, direction: str) -> None:
        try:
            self.toggle_flip(direction)
        except Exception as error:
            title = "水平翻转" if direction == "horizontal" else "垂直翻转"
            self._report_ui_action_error(title, error)

    def restore_crop_geometry_controls(self: Any) -> None:
        tool_groups = getattr(self, "_v072_tool_groups", ())
        if len(tool_groups) == 3:
            crop_group, _zoom_group, rotate_group = tool_groups

            for child in crop_group.winfo_children():
                child.destroy()
            self.crop_toggle_button = ttk.Button(
                crop_group,
                text="裁切",
                command=self._invoke_crop_editing,
            )
            self.crop_toggle_button.grid(row=0, column=0, padx=(0, 3))
            self.reset_crop_button = ttk.Button(
                crop_group,
                text="重置裁切",
                command=self.reset_crop,
            )
            self.reset_crop_button.grid(row=0, column=1, padx=(3, 0))

            for child in rotate_group.winfo_children():
                child.destroy()
            self.rotate_left_button = ttk.Button(
                rotate_group,
                text="左转 90°",
                command=lambda: self._invoke_rotation(-90),
            )
            self.rotate_left_button.grid(row=0, column=0, padx=(0, 2))
            self.rotate_right_button = ttk.Button(
                rotate_group,
                text="右转 90°",
                command=lambda: self._invoke_rotation(90),
            )
            self.rotate_right_button.grid(row=0, column=1, padx=2)
            self.rotation_status_label = ttk.Label(
                rotate_group,
                textvariable=self.rotation_status,
            )
            self.rotation_status_label.grid(row=0, column=2, padx=(5, 0))

        geometry_groups = getattr(self, "_v072_geometry_groups", ())
        if len(geometry_groups) == 3:
            _range_group, _straighten_group, transform_group = geometry_groups
            for child in transform_group.winfo_children():
                child.destroy()

            self.horizontal_flip_button = ttk.Button(
                transform_group,
                text="水平翻转",
                command=lambda: self._invoke_flip("horizontal"),
            )
            self.horizontal_flip_button.grid(row=0, column=0, padx=(0, 2))
            self.vertical_flip_button = ttk.Button(
                transform_group,
                text="垂直翻转",
                command=lambda: self._invoke_flip("vertical"),
            )
            self.vertical_flip_button.grid(row=0, column=1, padx=2)
            self.perspective_button = ttk.Button(
                transform_group,
                text="四角透视",
                command=self.toggle_perspective_mode,
            )
            self.perspective_button.grid(row=0, column=2, padx=2)
            self.reset_geometry_button = ttk.Button(
                transform_group,
                text="重置几何",
                command=self.reset_geometry,
            )
            self.reset_geometry_button.grid(row=0, column=3, padx=(2, 0))

        self.root.after_idle(self._layout_v072_preview_groups)
        self.root.after_idle(self._layout_v072_geometry_groups)

    app_class._build_ui = build_ui
    app_class._report_ui_action_error = report_action_error
    app_class._invoke_crop_editing = invoke_crop_editing
    app_class._invoke_rotation = invoke_rotation
    app_class._invoke_flip = invoke_flip
    app_class._restore_crop_geometry_controls = restore_crop_geometry_controls
    app_class._ui_action_bindings_applied = True

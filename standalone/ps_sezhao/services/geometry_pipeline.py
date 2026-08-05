from __future__ import annotations

from copy import deepcopy
from typing import Any, Type

import tkinter as tk
from tkinter import messagebox, ttk

from ..core.geometry import (
    GeometrySettings,
    IDENTITY_PERSPECTIVE,
    detect_frame_bounds,
    normalize_perspective,
    perspective_is_identity,
    rotate_geometry,
)
from ..workspace import FULL_CROP, clamp_crop


def apply_geometry_pipeline(app_class: Type[Any]) -> None:
    """Attach per-photo straighten, flip, perspective and range detection."""

    if getattr(app_class, "_geometry_pipeline_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_preview_panel = app_class._build_preview_panel
    original_load_index = app_class.load_index
    original_store_current_state = app_class._store_current_state
    original_clear_current_display = app_class._clear_current_display
    original_on_canvas_press = app_class.on_canvas_press
    original_draw_crop_overlay = app_class._draw_crop_overlay
    original_update_cursor = app_class._update_cursor
    original_item_snapshot = getattr(app_class, "item_snapshot", None)
    original_restore_snapshot = getattr(app_class, "restore_snapshot", None)
    original_rotate_current = getattr(app_class, "rotate_current", None)

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.straighten_angle = tk.DoubleVar(value=0.0)
        self.geometry_status = tk.StringVar(value="几何：未调整")
        self._perspective_editing = False
        self._perspective_points: list[tuple[float, float]] = []
        self._perspective_original = IDENTITY_PERSPECTIVE
        self.perspective_button: ttk.Button | None = None

    def build_preview_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_preview_panel(self, parent)
        parent.rowconfigure(1, weight=0)
        parent.rowconfigure(2, weight=1)
        self.canvas.grid_configure(row=2)
        for child in parent.winfo_children():
            info = child.grid_info() if hasattr(child, "grid_info") else {}
            if child is not self.canvas and str(info.get("row")) == "2":
                child.grid_configure(row=3)

        bar = ttk.LabelFrame(parent, text="几何校正", padding=(6, 4))
        bar.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        bar.columnconfigure(12, weight=1)
        ttk.Button(bar, text="自动范围", command=self.detect_frame_range).grid(row=0, column=0, padx=(0, 3))
        ttk.Label(bar, text="拉直").grid(row=0, column=1, padx=(7, 2))
        straighten = ttk.Spinbox(
            bar,
            from_=-15.0,
            to=15.0,
            increment=0.1,
            textvariable=self.straighten_angle,
            width=7,
            justify="right",
        )
        straighten.grid(row=0, column=2)
        straighten.bind("<Return>", lambda _event: self.commit_straighten())
        straighten.bind("<FocusOut>", lambda _event: self.commit_straighten())
        ttk.Label(bar, text="°").grid(row=0, column=3, padx=(2, 4))
        ttk.Button(bar, text="−0.1", width=5, command=lambda: self.adjust_straighten(-0.1)).grid(row=0, column=4, padx=2)
        ttk.Button(bar, text="+0.1", width=5, command=lambda: self.adjust_straighten(0.1)).grid(row=0, column=5, padx=2)
        ttk.Button(bar, text="水平翻转", command=lambda: self.toggle_flip("horizontal")).grid(row=0, column=6, padx=(7, 2))
        ttk.Button(bar, text="垂直翻转", command=lambda: self.toggle_flip("vertical")).grid(row=0, column=7, padx=2)
        self.perspective_button = ttk.Button(bar, text="四角透视", command=self.toggle_perspective_mode)
        self.perspective_button.grid(row=0, column=8, padx=(7, 2))
        ttk.Button(bar, text="重置几何", command=self.reset_geometry).grid(row=0, column=9, padx=2)
        ttk.Label(bar, textvariable=self.geometry_status, anchor="e").grid(row=0, column=12, sticky="e", padx=(8, 0))

    def current_geometry(self: Any) -> GeometrySettings:
        item = self.current_item()
        return GeometrySettings.from_dict(None if item is None else item.geometry)

    def set_current_geometry(self: Any, geometry: GeometrySettings) -> None:
        item = self.current_item()
        if item is None:
            return
        item.geometry = geometry.sanitized().to_dict()
        self._load_geometry_ui(item)
        self._refresh_geometry_preview()

    def load_geometry_ui(self: Any, item: Any | None = None) -> None:
        item = self.current_item() if item is None else item
        geometry = GeometrySettings.from_dict(None if item is None else item.geometry)
        self.straighten_angle.set(round(geometry.straighten, 2))
        details: list[str] = []
        if abs(geometry.straighten) >= 0.05:
            details.append(f"拉直 {geometry.straighten:+.1f}°")
        if geometry.flip_horizontal:
            details.append("水平翻转")
        if geometry.flip_vertical:
            details.append("垂直翻转")
        if not perspective_is_identity(geometry.perspective):
            details.append("四角透视")
        if geometry.detection_method:
            details.append(f"范围可信度 {geometry.detection_confidence * 100:.0f}%")
        self.geometry_status.set("几何：未调整" if not details else "几何：" + " · ".join(details))

    def load_index(self: Any, index: int) -> None:
        original_load_index(self, index)
        if 0 <= index < len(self.items):
            self._load_geometry_ui(self.items[index])

    def store_current_state(self: Any) -> None:
        original_store_current_state(self)
        item = self.current_item()
        if item is None:
            return
        geometry = GeometrySettings.from_dict(item.geometry)
        geometry = GeometrySettings(
            straighten=float(self.straighten_angle.get()),
            flip_horizontal=geometry.flip_horizontal,
            flip_vertical=geometry.flip_vertical,
            perspective=geometry.perspective,
            detection_confidence=geometry.detection_confidence,
            detection_method=geometry.detection_method,
        ).sanitized()
        item.geometry = geometry.to_dict()

    def refresh_geometry_preview(self: Any) -> None:
        item = self.current_item()
        if item is None or self.current_index is None:
            return
        self._store_current_state()
        if hasattr(self, "_record_history"):
            self._record_history(force=True, kind="geometry")
        self._update_tree_row(self.current_index)
        index = self.current_index
        self.load_index(index)
        if hasattr(self, "_schedule_project_save"):
            self._schedule_project_save()

    def commit_straighten(self: Any) -> str:
        item = self.current_item()
        if item is None:
            return "break"
        try:
            value = float(self.straighten_angle.get())
        except (TypeError, ValueError, tk.TclError):
            value = 0.0
        geometry = GeometrySettings.from_dict(item.geometry)
        value = max(-15.0, min(15.0, value))
        if abs(value - geometry.straighten) < 1e-6:
            self.straighten_angle.set(value)
            return "break"
        self.set_current_geometry(
            GeometrySettings(
                straighten=value,
                flip_horizontal=geometry.flip_horizontal,
                flip_vertical=geometry.flip_vertical,
                perspective=geometry.perspective,
                detection_confidence=geometry.detection_confidence,
                detection_method=geometry.detection_method,
            )
        )
        self.status.set(f"拉直角度已设为 {value:+.1f}°。")
        return "break"

    def adjust_straighten(self: Any, delta: float) -> None:
        try:
            value = float(self.straighten_angle.get()) + float(delta)
        except (TypeError, ValueError, tk.TclError):
            value = float(delta)
        self.straighten_angle.set(round(max(-15.0, min(15.0, value)), 2))
        self.commit_straighten()

    def toggle_flip(self: Any, direction: str) -> None:
        item = self.current_item()
        if item is None:
            return
        geometry = GeometrySettings.from_dict(item.geometry)
        self.set_current_geometry(
            GeometrySettings(
                straighten=geometry.straighten,
                flip_horizontal=(not geometry.flip_horizontal) if direction == "horizontal" else geometry.flip_horizontal,
                flip_vertical=(not geometry.flip_vertical) if direction == "vertical" else geometry.flip_vertical,
                perspective=geometry.perspective,
                detection_confidence=geometry.detection_confidence,
                detection_method=geometry.detection_method,
            )
        )
        self.status.set("已切换水平翻转。" if direction == "horizontal" else "已切换垂直翻转。")

    def reset_geometry(self: Any) -> None:
        item = self.current_item()
        if item is None:
            return
        item.crop = FULL_CROP
        self.crop_norm = FULL_CROP
        self.set_current_geometry(GeometrySettings())
        self.status.set("几何校正和裁切已恢复默认。")

    def detect_frame_range(self: Any) -> None:
        if self.preview_source is None:
            messagebox.showinfo("尚未就绪", "请等待当前图片的编辑代理完成。")
            return
        detection = detect_frame_bounds(self.preview_source)
        item = self.current_item()
        if item is None:
            return
        geometry = GeometrySettings.from_dict(item.geometry)
        item.geometry = GeometrySettings(
            straighten=geometry.straighten,
            flip_horizontal=geometry.flip_horizontal,
            flip_vertical=geometry.flip_vertical,
            perspective=geometry.perspective,
            detection_confidence=detection.confidence,
            detection_method=detection.method,
        ).to_dict()
        self.crop_norm = clamp_crop(detection.crop)
        item.crop = self.crop_norm
        self._update_crop_status()
        self._update_tree_row(self.current_index)
        self.draw_preview()
        self._store_current_state()
        self._load_geometry_ui(item)
        if hasattr(self, "_record_history"):
            self._record_history(force=True, kind="auto-range")
        if hasattr(self, "_schedule_project_save"):
            self._schedule_project_save()
        if detection.used_fallback:
            self.status.set(
                f"自动范围可信度 {detection.confidence * 100:.0f}%，已保留完整画面，请手动裁切。"
            )
        else:
            self.status.set(f"自动范围完成，可信度 {detection.confidence * 100:.0f}%。")

    def toggle_perspective_mode(self: Any) -> None:
        item = self.current_item()
        if item is None or self.preview_source is None:
            messagebox.showinfo("尚未就绪", "请等待当前图片的编辑代理完成。")
            return
        if self._perspective_editing:
            self._cancel_perspective_mode(restore=True)
            return
        geometry = GeometrySettings.from_dict(item.geometry)
        self._perspective_original = geometry.perspective
        self._perspective_points = []
        self._perspective_editing = True
        item.geometry = GeometrySettings(
            straighten=geometry.straighten,
            flip_horizontal=geometry.flip_horizontal,
            flip_vertical=geometry.flip_vertical,
            perspective=IDENTITY_PERSPECTIVE,
            detection_confidence=geometry.detection_confidence,
            detection_method=geometry.detection_method,
        ).to_dict()
        if self.perspective_button is not None:
            self.perspective_button.configure(text="取消四角")
        self.interaction_mode.set("perspective")
        self.status.set("请依次点击左上、右上、右下、左下四个角。")
        self._refresh_geometry_preview()

    def cancel_perspective_mode(self: Any, *, restore: bool) -> None:
        item = self.current_item()
        if item is not None and restore:
            geometry = GeometrySettings.from_dict(item.geometry)
            item.geometry = GeometrySettings(
                straighten=geometry.straighten,
                flip_horizontal=geometry.flip_horizontal,
                flip_vertical=geometry.flip_vertical,
                perspective=self._perspective_original,
                detection_confidence=geometry.detection_confidence,
                detection_method=geometry.detection_method,
            ).to_dict()
        self._perspective_editing = False
        self._perspective_points = []
        self.interaction_mode.set("pan")
        if self.perspective_button is not None:
            self.perspective_button.configure(text="四角透视")
        self._update_cursor()
        if restore and item is not None:
            self._refresh_geometry_preview()

    def on_canvas_press(self: Any, event: tk.Event) -> None:
        if not self._perspective_editing:
            original_on_canvas_press(self, event)
            return
        point = self.map_canvas_to_preview(event.x, event.y)
        if point is None or self.preview_source is None:
            return
        height, width = self.preview_source.shape[:2]
        normalized = (
            min(1.0, max(0.0, point[0] / max(1, width - 1))),
            min(1.0, max(0.0, point[1] / max(1, height - 1))),
        )
        self._perspective_points.append(normalized)
        self.draw_preview()
        count = len(self._perspective_points)
        if count < 4:
            names = ("右上", "右下", "左下")
            self.status.set(f"已记录 {count}/4，下一点：{names[count - 1]}。")
            return
        perspective = normalize_perspective(self._perspective_points)
        if perspective_is_identity(perspective) and tuple(self._perspective_points) != IDENTITY_PERSPECTIVE:
            messagebox.showwarning("四角无效", "四个点形成的区域过小或顺序不正确，请重新选择。")
            self._perspective_points = []
            self.draw_preview()
            return
        item = self.current_item()
        if item is not None:
            geometry = GeometrySettings.from_dict(item.geometry)
            item.geometry = GeometrySettings(
                straighten=geometry.straighten,
                flip_horizontal=geometry.flip_horizontal,
                flip_vertical=geometry.flip_vertical,
                perspective=perspective,
                detection_confidence=geometry.detection_confidence,
                detection_method=geometry.detection_method,
            ).to_dict()
        self._perspective_editing = False
        self._perspective_points = []
        self.interaction_mode.set("pan")
        if self.perspective_button is not None:
            self.perspective_button.configure(text="四角透视")
        self.status.set("四角透视已应用。")
        self._refresh_geometry_preview()

    def draw_crop_overlay(self: Any) -> None:
        original_draw_crop_overlay(self)
        self._draw_perspective_overlay()

    def draw_perspective_overlay(self: Any) -> None:
        if not self._perspective_editing or self.display_pil is None:
            return
        offset_x, offset_y, scale, width, height = self.canvas_geometry
        points = [
            (offset_x + x * width * scale, offset_y + y * height * scale)
            for x, y in self._perspective_points
        ]
        if len(points) >= 2:
            flattened = [coordinate for point in points for coordinate in point]
            self.canvas.create_line(*flattened, fill="#5de1ff", width=2)
        for index, (x, y) in enumerate(points, start=1):
            self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill="#5de1ff", outline="#111")
            self.canvas.create_text(x + 10, y - 10, text=str(index), fill="#5de1ff", anchor="sw")

    def update_cursor(self: Any) -> None:
        if self._perspective_editing:
            self.canvas.configure(cursor="crosshair")
            return
        original_update_cursor(self)

    def clear_current_display(self: Any) -> None:
        self._perspective_editing = False
        self._perspective_points = []
        if self.perspective_button is not None:
            self.perspective_button.configure(text="四角透视")
        original_clear_current_display(self)
        self.straighten_angle.set(0.0)
        self.geometry_status.set("几何：未调整")

    def item_snapshot(self: Any, index: int | None = None) -> dict[str, Any] | None:
        if original_item_snapshot is None:
            return None
        snapshot = original_item_snapshot(self, index)
        target = self.current_index if index is None else index
        if snapshot is not None and target is not None and 0 <= target < len(self.items):
            snapshot["geometry"] = deepcopy(self.items[target].geometry)
        return snapshot

    def restore_snapshot(self: Any, snapshot: dict[str, Any]) -> None:
        item = self.current_item()
        if item is not None:
            item.geometry = deepcopy(snapshot.get("geometry") or {})
        if original_restore_snapshot is not None:
            original_restore_snapshot(self, snapshot)
        if item is not None:
            self._load_geometry_ui(item)
            self._refresh_geometry_preview()

    def rotate_current(self: Any, clockwise_degrees: int) -> None:
        item = self.current_item()
        before = GeometrySettings.from_dict(None if item is None else item.geometry)
        if original_rotate_current is not None:
            original_rotate_current(self, clockwise_degrees)
        item = self.current_item()
        if item is None:
            return
        item.geometry = rotate_geometry(before, clockwise_degrees).to_dict()
        self._load_geometry_ui(item)
        self._refresh_geometry_preview()

    app_class._build_variables = build_variables
    app_class._build_preview_panel = build_preview_panel
    app_class.load_index = load_index
    app_class._store_current_state = store_current_state
    app_class._clear_current_display = clear_current_display
    app_class.on_canvas_press = on_canvas_press
    app_class._draw_crop_overlay = draw_crop_overlay
    app_class._update_cursor = update_cursor
    app_class._current_geometry = current_geometry
    app_class._set_current_geometry = set_current_geometry
    app_class._load_geometry_ui = load_geometry_ui
    app_class._refresh_geometry_preview = refresh_geometry_preview
    app_class.commit_straighten = commit_straighten
    app_class.adjust_straighten = adjust_straighten
    app_class.toggle_flip = toggle_flip
    app_class.reset_geometry = reset_geometry
    app_class.detect_frame_range = detect_frame_range
    app_class.toggle_perspective_mode = toggle_perspective_mode
    app_class._cancel_perspective_mode = cancel_perspective_mode
    app_class._draw_perspective_overlay = draw_perspective_overlay
    if original_item_snapshot is not None:
        app_class.item_snapshot = item_snapshot
    if original_restore_snapshot is not None:
        app_class.restore_snapshot = restore_snapshot
    if original_rotate_current is not None:
        app_class.rotate_current = rotate_current
    app_class._geometry_pipeline_applied = True

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Type

import tkinter as tk
from tkinter import messagebox, ttk

from ..app_v051_raw_patch import DEMOSAIC_LABELS, HIGHLIGHT_LABELS, WB_LABELS
from ..raw_io import RawDecodeSettings
from ..workspace import PhotoState

MODULE_LABELS = {
    "base": "胶片基底与分析结果",
    "styles": "扫描仪与胶卷风格",
    "tone": "曝光与明暗",
    "color": "白平衡与 RGB",
    "raw": "RAW 解码设置",
    "geometry": "旋转、拉直、翻转与透视",
    "crop": "裁切范围",
    "output": "输出格式与质量",
}

STYLE_KEYS = {"profile", "style_strength", "scanner_profile", "scanner_strength"}
TONE_KEYS = {
    "exposure",
    "contrast",
    "gamma",
    "saturation",
    "black_point",
    "white_point",
    "shadows",
    "highlights",
}
COLOR_KEYS = {"temperature", "tint", "red_gain", "green_gain", "blue_gain"}
BASE_KEYS = {"base_adjust"}


def copy_modules(
    source: PhotoState,
    target: PhotoState,
    modules: Iterable[str],
) -> PhotoState:
    """Return a complete target copy with only requested modules replaced."""

    selected = set(modules)
    result = deepcopy(target)
    source_controls = dict(source.controls)
    target_controls = dict(result.controls)

    def copy_control_keys(keys: set[str]) -> None:
        for key in keys:
            if key in source_controls:
                target_controls[key] = deepcopy(source_controls[key])

    if "base" in selected:
        result.analysis = deepcopy(source.analysis)
        copy_control_keys(BASE_KEYS)
    if "styles" in selected:
        copy_control_keys(STYLE_KEYS)
    if "tone" in selected:
        copy_control_keys(TONE_KEYS)
    if "color" in selected:
        copy_control_keys(COLOR_KEYS)
    result.controls = target_controls

    if "raw" in selected:
        result.raw_settings = deepcopy(source.raw_settings)
    if "geometry" in selected:
        result.rotation = int(source.rotation)
        result.geometry = deepcopy(source.geometry)
    if "crop" in selected:
        result.crop = tuple(source.crop)
    if "output" in selected:
        result.output_settings = deepcopy(source.output_settings)
    result.__post_init__()
    return result


def apply_sync_pipeline(app_class: Type[Any]) -> None:
    """Replace duplicate sync actions with one module-selectable transaction."""

    if getattr(app_class, "_sync_pipeline_applied", False):
        return

    original_build_file_panel = app_class._build_file_panel
    original_store_current_state = app_class._store_current_state
    original_load_index = app_class.load_index
    original_item_snapshot = getattr(app_class, "item_snapshot", None)
    original_restore_snapshot = getattr(app_class, "restore_snapshot", None)

    def build_file_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_file_panel(self, parent)
        for widget in parent.winfo_children():
            if not isinstance(widget, ttk.Frame):
                continue
            for child in widget.winfo_children():
                if not isinstance(child, ttk.Button):
                    continue
                try:
                    text = str(child.cget("text"))
                except tk.TclError:
                    continue
                if text in {"同步参数到选中", "同步裁切到选中"}:
                    child.grid_remove()
            info = widget.grid_info()
            if str(info.get("row")) == "2":
                self.sync_settings_button = ttk.Button(
                    widget,
                    text="复制设置到选中…",
                    command=self.open_sync_dialog,
                )
                self.sync_settings_button.grid(
                    row=0,
                    column=0,
                    columnspan=2,
                    sticky="ew",
                )
                break

    def raw_settings_for_item(self: Any, item: PhotoState) -> RawDecodeSettings:
        if item.raw_settings:
            return RawDecodeSettings.from_dict(item.raw_settings)
        return self.raw_settings_value() if hasattr(self, "raw_settings_value") else RawDecodeSettings()

    def output_settings_for_item(self: Any, item: PhotoState) -> dict[str, Any]:
        if item.output_settings:
            return dict(item.output_settings)
        return {
            "format_label": self.output_format_label.get()
            if hasattr(self, "output_format_label")
            else "16 位 TIFF（无损）",
            "jpeg_quality": self._output_quality() if hasattr(self, "_output_quality") else 95,
        }

    def store_current_state(self: Any) -> None:
        original_store_current_state(self)
        item = self.current_item()
        if item is None:
            return
        if hasattr(self, "raw_settings_value"):
            item.raw_settings = self.raw_settings_value().to_dict()
        if hasattr(self, "output_format_label"):
            item.output_settings = {
                "format_label": self.output_format_label.get(),
                "jpeg_quality": self._output_quality() if hasattr(self, "_output_quality") else 95,
            }

    def load_index(self: Any, index: int) -> None:
        original_load_index(self, index)
        if index < 0 or index >= len(self.items):
            return
        item = self.items[index]
        self._apply_item_raw_settings(item)
        self._apply_item_output_settings(item)

    def apply_item_raw_settings(self: Any, item: PhotoState) -> None:
        if not hasattr(self, "raw_wb_label"):
            return
        settings = self._raw_settings_for_item(item).sanitized()
        inverse_wb = {value: label for label, value in WB_LABELS.items()}
        inverse_highlight = {value: label for label, value in HIGHLIGHT_LABELS.items()}
        inverse_demosaic = {value: label for label, value in DEMOSAIC_LABELS.items()}
        self.raw_wb_label.set(inverse_wb.get(settings.wb_mode, "相机拍摄白平衡"))
        self.raw_highlight_label.set(inverse_highlight.get(settings.highlight_mode, "混合高光（推荐）"))
        self.raw_demosaic_label.set(inverse_demosaic.get(settings.demosaic, "AHD 标准质量"))
        self.raw_use_embedded_preview.set(settings.use_embedded_preview)
        self.raw_half_size_preview.set(settings.half_size_preview)
        for variable, value in zip(self.raw_custom_wb_vars, settings.custom_wb):
            variable.set(f"{value:.3f}")
        self._update_custom_wb_state()

    def apply_item_output_settings(self: Any, item: PhotoState) -> None:
        if not hasattr(self, "output_format_label"):
            return
        settings = self._output_settings_for_item(item)
        self.output_format_label.set(str(settings.get("format_label") or "16 位 TIFF（无损）"))
        try:
            quality = min(100, max(1, int(settings.get("jpeg_quality", 95))))
        except (TypeError, ValueError):
            quality = 95
        self.jpeg_quality.set(quality)
        self._update_output_quality_state()

    def open_sync_dialog(self: Any) -> None:
        source = self.current_item()
        if source is None or self.current_index is None:
            return
        targets = [index for index in self.selected_indices() if index != self.current_index]
        if not targets:
            messagebox.showinfo("没有目标图片", "请在左侧同时选择当前图片和至少一张目标图片。")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("复制设置到选中图片")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text=f"从“{source.path.name}”复制到 {len(targets)} 张目标图片",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        variables: dict[str, tk.BooleanVar] = {}
        defaults = {"base", "styles", "tone", "color"}
        for row, (key, label) in enumerate(MODULE_LABELS.items(), start=1):
            variable = tk.BooleanVar(value=key in defaults)
            variables[key] = variable
            ttk.Checkbutton(frame, text=label, variable=variable).grid(
                row=row,
                column=0,
                columnspan=2,
                sticky="w",
                pady=2,
            )

        quick = ttk.Frame(frame)
        quick.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(8, 5))
        ttk.Button(
            quick,
            text="仅调色",
            command=lambda: self._set_sync_selection(variables, {"base", "styles", "tone", "color"}),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            quick,
            text="固定机位几何",
            command=lambda: self._set_sync_selection(variables, {"geometry", "crop"}),
        ).pack(side="left", padx=4)
        ttk.Button(
            quick,
            text="全部设置",
            command=lambda: self._set_sync_selection(variables, set(MODULE_LABELS)),
        ).pack(side="left", padx=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=11, column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(
            buttons,
            text="应用到选中图片",
            command=lambda: self._apply_sync_dialog(dialog, variables, targets),
        ).pack(side="right")
        dialog.grab_set()
        dialog.wait_visibility()
        dialog.focus_set()

    def set_sync_selection(
        self: Any,
        variables: dict[str, tk.BooleanVar],
        selected: set[str],
    ) -> None:
        for key, variable in variables.items():
            variable.set(key in selected)

    def apply_sync_dialog(
        self: Any,
        dialog: tk.Toplevel,
        variables: dict[str, tk.BooleanVar],
        targets: list[int],
    ) -> None:
        modules = {key for key, variable in variables.items() if variable.get()}
        if not modules:
            messagebox.showinfo("尚未选择", "请选择至少一个需要复制的设置模块。", parent=dialog)
            return
        self._store_current_state()
        source = self.current_item()
        if source is None:
            return

        try:
            replacements = {
                index: copy_modules(source, self.items[index], modules)
                for index in targets
            }
        except Exception as exc:
            messagebox.showerror("复制设置失败", str(exc), parent=dialog)
            return

        for index in targets:
            if hasattr(self, "_history_for"):
                self._history_for(index)
        for index, replacement in replacements.items():
            self.items[index] = replacement
            self._update_tree_row(index)
        if hasattr(self, "_record_history"):
            self._record_history(force=True, kind="sync-modules", indices=targets)
        if hasattr(self, "_schedule_project_save"):
            self._schedule_project_save()
        names = "、".join(MODULE_LABELS[key] for key in MODULE_LABELS if key in modules)
        self.status.set(f"已将 {names} 复制到 {len(targets)} 张图片。")
        dialog.destroy()

    def item_snapshot(self: Any, index: int | None = None) -> dict[str, Any] | None:
        if original_item_snapshot is None:
            return None
        snapshot = original_item_snapshot(self, index)
        target = self.current_index if index is None else index
        if snapshot is not None and target is not None and 0 <= target < len(self.items):
            item = self.items[target]
            snapshot["raw_settings"] = deepcopy(item.raw_settings)
            snapshot["output_settings"] = deepcopy(item.output_settings)
        return snapshot

    def restore_snapshot(self: Any, snapshot: dict[str, Any]) -> None:
        item = self.current_item()
        if item is not None:
            item.raw_settings = deepcopy(snapshot.get("raw_settings") or {})
            item.output_settings = deepcopy(snapshot.get("output_settings") or {})
        if original_restore_snapshot is not None:
            original_restore_snapshot(self, snapshot)
        item = self.current_item()
        if item is not None:
            self._apply_item_raw_settings(item)
            self._apply_item_output_settings(item)

    app_class._build_file_panel = build_file_panel
    app_class._store_current_state = store_current_state
    app_class.load_index = load_index
    app_class._raw_settings_for_item = raw_settings_for_item
    app_class._output_settings_for_item = output_settings_for_item
    app_class._apply_item_raw_settings = apply_item_raw_settings
    app_class._apply_item_output_settings = apply_item_output_settings
    app_class.open_sync_dialog = open_sync_dialog
    app_class._set_sync_selection = set_sync_selection
    app_class._apply_sync_dialog = apply_sync_dialog
    if original_item_snapshot is not None:
        app_class.item_snapshot = item_snapshot
    if original_restore_snapshot is not None:
        app_class.restore_snapshot = restore_snapshot
    app_class._sync_pipeline_applied = True

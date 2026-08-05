from __future__ import annotations

from copy import deepcopy
import time
from typing import Any, Iterator, Type

import numpy as np
import tkinter as tk
from tkinter import ttk

from .engine import Analysis, Controls
from .history_state import HistoryStack
from .workspace import clamp_crop

BASE_CHANNELS = (("R", 0), ("G", 1), ("B", 2))
BASE_DIRECT_MIN = 0
BASE_DIRECT_MAX = 384
NEUTRAL_KEYS = (("R", "red_gain"), ("G", "green_gain"), ("B", "blue_gain"))


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def apply_v054_patch(app_class: Type[Any]) -> None:
    """Add direct base values, visible neutral gains and per-photo undo/redo."""

    if getattr(app_class, "_v054_history_direct_applied", False):
        return

    original_build_ui = app_class._build_ui
    original_controls_value = app_class.controls_value
    original_apply_controls = app_class.apply_controls
    original_update_base_value_text = app_class.update_base_value_text
    original_auto_analyze = app_class.auto_analyze
    original_apply_pick = app_class._apply_pick
    original_load_index = app_class.load_index
    original_control_changed = app_class._control_changed
    original_on_canvas_release = app_class.on_canvas_release
    original_toggle_crop_editing = app_class.toggle_crop_editing
    original_reset_controls = app_class.reset_controls
    original_sync_controls_selected = app_class.sync_controls_selected
    original_sync_crop_selected = app_class.sync_crop_selected

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._v054_histories: dict[str, HistoryStack] = {}
        self._history_restoring = False
        self._history_last_time = 0.0
        self._history_last_kind = ""
        self._configure_direct_base_panel()
        self._add_neutral_gain_panel()
        self._add_history_buttons()
        self._bind_history_shortcuts()
        self._update_history_buttons()

    def configure_direct_base_panel(self: Any) -> None:
        variable_names = {str(variable) for variable in self.base_adjust_units.values()}
        base_frame: ttk.LabelFrame | None = None
        for widget in _walk_widgets(self.controls):
            if isinstance(widget, tk.Scale) and str(widget.cget("variable")) in variable_names:
                widget.configure(from_=BASE_DIRECT_MIN, to=BASE_DIRECT_MAX, resolution=1)
            elif isinstance(widget, ttk.LabelFrame):
                try:
                    if str(widget.cget("text")).startswith("胶片基底手动微调"):
                        widget.configure(text="胶片基底（直接数值） · v0.5.4")
                        base_frame = widget
                except tk.TclError:
                    pass
        if base_frame is not None:
            for widget in _walk_widgets(base_frame):
                if isinstance(widget, ttk.Button):
                    try:
                        if "重置胶片基底" in str(widget.cget("text")):
                            widget.configure(text="恢复为识别值")
                    except tk.TclError:
                        pass
                elif isinstance(widget, ttk.Label):
                    try:
                        text = str(widget.cget("text"))
                    except tk.TclError:
                        text = ""
                    if "相对原图" in text or "等效偏移" in text:
                        widget.configure(
                            text="这里直接填写最终使用的 8 位等效 R/G/B。0–255 是常规范围，256–384 用于极端胶片基底。"
                        )

    def add_neutral_gain_panel(self: Any) -> None:
        row = self.controls.grid_size()[1]
        frame = ttk.LabelFrame(self.controls, text="中性灰校正（RGB 输出增益）", padding=7)
        frame.grid(row=row, column=0, sticky="ew", pady=(2, 12))
        frame.columnconfigure(0, weight=1)
        ttk.Label(
            frame,
            text="中性灰吸管只修改下面三个输出增益。1.000 表示不校正；数值可直接输入，也可用 − / + 微调。",
            foreground="#555",
            wraplength=295,
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        for row_index, (channel, key) in enumerate(NEUTRAL_KEYS, start=1):
            line = ttk.Frame(frame)
            line.grid(row=row_index, column=0, sticky="ew", pady=2)
            line.columnconfigure(1, weight=1)
            ttk.Label(line, text=f"{channel} 增益", width=7).grid(row=0, column=0, sticky="w")
            ttk.Button(line, text="−", width=3, command=lambda k=key: self.adjust_control(k, -1)).grid(row=0, column=1, sticky="e")
            entry = ttk.Entry(line, textvariable=self.entry_vars[key], width=9, justify="right")
            entry.grid(row=0, column=2, padx=2)
            ttk.Button(line, text="+", width=3, command=lambda k=key: self.adjust_control(k, 1)).grid(row=0, column=3)
            entry.bind("<Return>", lambda _event, k=key: self.commit_entry(k))
            entry.bind("<FocusOut>", lambda _event, k=key: self.commit_entry(k))
            entry.bind("<Up>", lambda _event, k=key: self.adjust_control(k, 1))
            entry.bind("<Down>", lambda _event, k=key: self.adjust_control(k, -1))
        ttk.Button(frame, text="中性灰校正恢复 1.000", command=self.reset_neutral_gains).grid(
            row=4, column=0, sticky="ew", pady=(6, 0)
        )

    def add_history_buttons(self: Any) -> None:
        toolbar = None
        for child in self.root.winfo_children():
            info = child.grid_info() if hasattr(child, "grid_info") else {}
            if isinstance(child, ttk.Frame) and str(info.get("row")) == "0":
                toolbar = child
                break
        if toolbar is None:
            return
        self.undo_button = ttk.Button(toolbar, text="↶ 撤销", command=self.undo_edit)
        self.redo_button = ttk.Button(toolbar, text="↷ 重做", command=self.redo_edit)
        self.undo_button.grid(row=1, column=0, columnspan=2, sticky="ew", padx=3, pady=(5, 0))
        self.redo_button.grid(row=1, column=2, columnspan=2, sticky="ew", padx=3, pady=(5, 0))
        ttk.Label(toolbar, text="Ctrl/Cmd+Z · Ctrl/Cmd+Y", foreground="#666").grid(
            row=1, column=4, columnspan=4, sticky="w", padx=(8, 0), pady=(5, 0)
        )

    def bind_history_shortcuts(self: Any) -> None:
        self.root.bind_all("<Control-z>", lambda _event: self.undo_edit())
        self.root.bind_all("<Control-y>", lambda _event: self.redo_edit())
        self.root.bind_all("<Control-Shift-Z>", lambda _event: self.redo_edit())
        self.root.bind_all("<Command-z>", lambda _event: self.undo_edit())
        self.root.bind_all("<Command-Shift-Z>", lambda _event: self.redo_edit())

    def detected_base(self: Any) -> np.ndarray:
        if self.analysis is None:
            return np.zeros(3, dtype=np.float32)
        return np.asarray(self.analysis.base, dtype=np.float32)

    def direct_base_units(self: Any) -> np.ndarray:
        return np.asarray(
            [float(self.base_adjust_units[channel].get()) for channel, _index in BASE_CHANNELS],
            dtype=np.float32,
        )

    def set_direct_base_units(self: Any, values: Any) -> None:
        array = np.asarray(values, dtype=np.float32).reshape(3)
        for (channel, _index), value in zip(BASE_CHANNELS, array):
            unit = int(round(float(np.clip(value, BASE_DIRECT_MIN, BASE_DIRECT_MAX))))
            self.base_adjust_units[channel].set(unit)
            self.base_adjust_entries[channel].set(str(unit))

    def controls_value(self: Any) -> Controls:
        controls = original_controls_value(self)
        payload = controls.to_dict()
        direct = self.direct_base_units() / 255.0
        payload["base_adjust"] = tuple(float(value) for value in direct - self.detected_base())
        return Controls.from_dict(payload)

    def apply_controls(self: Any, controls: Controls) -> None:
        original_apply_controls(self, controls)
        direct = (self.detected_base() + np.asarray(controls.base_adjust, dtype=np.float32)) * 255.0
        self.set_direct_base_units(direct)
        self.update_base_value_text()

    def update_base_value_text(self: Any) -> None:
        if self.analysis is None:
            original_update_base_value_text(self)
            return
        detected = self.detected_base() * 255.0
        direct = self.direct_base_units()
        detected_text = " / ".join(str(int(round(float(value)))) for value in detected)
        direct_text = " / ".join(str(int(round(float(value)))) for value in direct)
        self.base_value_text.set(f"原图识别 R/G/B：{detected_text}　｜　最终使用：{direct_text}")

    def commit_base_entry(self: Any, channel: str) -> str:
        try:
            value = float(self.base_adjust_entries[channel].get().strip())
        except (TypeError, ValueError):
            value = float(self.base_adjust_units[channel].get())
        value = int(round(min(BASE_DIRECT_MAX, max(BASE_DIRECT_MIN, value))))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()
        return "break"

    def adjust_base(self: Any, channel: str, direction: int) -> str:
        value = int(round(float(self.base_adjust_units[channel].get()) + int(direction)))
        value = min(BASE_DIRECT_MAX, max(BASE_DIRECT_MIN, value))
        self.base_adjust_units[channel].set(value)
        self.base_adjust_entries[channel].set(str(value))
        self.base_adjust_changed()
        return "break"

    def reset_base_adjust(self: Any) -> None:
        self.set_direct_base_units(self.detected_base() * 255.0)
        self.base_adjust_changed()

    def reset_neutral_gains(self: Any) -> None:
        for key in ("red_gain", "green_gain", "blue_gain"):
            self.vars[key].set(1.0)
            self.entry_vars[key].set(self._format_value(key, 1.0))
        self._control_changed()
        self.status.set("中性灰 RGB 输出增益已恢复为 1.000。")

    def item_key(self: Any, index: int | None = None) -> str | None:
        target = self.current_index if index is None else index
        if target is None or target < 0 or target >= len(self.items):
            return None
        return str(self.items[target].path.resolve())

    def item_snapshot(self: Any, index: int | None = None) -> dict[str, Any] | None:
        target = self.current_index if index is None else index
        if target is None or target < 0 or target >= len(self.items):
            return None
        if target == self.current_index and not self._history_restoring:
            self._store_current_state()
        item = self.items[target]
        return {
            "controls": deepcopy(item.controls),
            "analysis": deepcopy(item.analysis),
            "crop": tuple(item.crop),
        }

    def history_for(self: Any, index: int | None = None) -> HistoryStack | None:
        key = self.item_key(index)
        if key is None:
            return None
        stack = self._v054_histories.get(key)
        if stack is None:
            stack = HistoryStack(limit=60)
            snapshot = self.item_snapshot(index)
            if snapshot is not None:
                stack.reset(snapshot)
            self._v054_histories[key] = stack
        return stack

    def record_history(self: Any, *, force: bool = False, kind: str = "continuous", indices: list[int] | None = None) -> None:
        if self._history_restoring:
            return
        targets = indices if indices is not None else ([self.current_index] if self.current_index is not None else [])
        now = time.monotonic()
        replace_last = not force and kind == self._history_last_kind and now - self._history_last_time < 0.35
        for index in targets:
            if index is None:
                continue
            stack = self.history_for(index)
            snapshot = self.item_snapshot(index)
            if stack is not None and snapshot is not None:
                stack.record(snapshot, replace_last=replace_last)
        self._history_last_time = now
        self._history_last_kind = kind
        self._update_history_buttons()

    def restore_snapshot(self: Any, snapshot: dict[str, Any]) -> None:
        item = self.current_item()
        if item is None:
            return
        self._history_restoring = True
        self._loading_item = True
        try:
            item.controls = deepcopy(snapshot.get("controls") or {})
            item.analysis = deepcopy(snapshot.get("analysis"))
            item.crop = clamp_crop(snapshot.get("crop"))
            self.analysis = Analysis.from_dict(item.analysis) if item.analysis else None
            self.crop_norm = item.crop
            self.apply_controls(Controls.from_dict(item.controls))
            self._update_crop_status()
            self._update_tree_row(self.current_index)
            self.update_base_value_text()
            self.zoom_fit_view()
            self.schedule_render(0)
        finally:
            self._loading_item = False
            self._history_restoring = False
        self.status.set("已恢复上一项编辑。")
        self._update_history_buttons()

    def undo_edit(self: Any) -> str:
        stack = self.history_for()
        snapshot = stack.undo() if stack is not None else None
        if snapshot is not None:
            self.restore_snapshot(snapshot)
        else:
            self.status.set("没有可撤销的操作。")
        return "break"

    def redo_edit(self: Any) -> str:
        stack = self.history_for()
        snapshot = stack.redo() if stack is not None else None
        if snapshot is not None:
            self.restore_snapshot(snapshot)
            self.status.set("已重做下一项编辑。")
        else:
            self.status.set("没有可重做的操作。")
        return "break"

    def update_history_buttons(self: Any) -> None:
        stack = self.history_for() if self.current_index is not None and self.items else None
        if hasattr(self, "undo_button"):
            self.undo_button.configure(state="normal" if stack and stack.can_undo else "disabled")
        if hasattr(self, "redo_button"):
            self.redo_button.configure(state="normal" if stack and stack.can_redo else "disabled")

    def load_index(self: Any, index: int) -> None:
        original_load_index(self, index)
        if self.analysis is not None:
            controls = Controls.from_dict(self.current_item().controls if self.current_item() else None)
            self.apply_controls(controls)
        self.history_for(index)
        self._update_history_buttons()

    def control_changed(self: Any) -> None:
        original_control_changed(self)
        self._record_history(force=False, kind="control")

    def auto_analyze(self: Any) -> None:
        original_auto_analyze(self)
        if self.analysis is not None:
            self.set_direct_base_units(self.detected_base() * 255.0)
            self._store_current_state()
            self.update_base_value_text()
            self.schedule_render(0)
            self._record_history(force=True, kind="analysis")

    def apply_pick(self: Any, x: int, y: int) -> None:
        mode = self.pick_mode
        original_apply_pick(self, x, y)
        if mode == "base" and self.analysis is not None:
            self.set_direct_base_units(self.detected_base() * 255.0)
            self._store_current_state()
            self.update_base_value_text()
            self.schedule_render(0)
        if mode == "neutral":
            self.status.set("中性灰吸管已更新 R/G/B 输出增益；可在右侧直接修改。")
        self._record_history(force=True, kind="picker")

    def on_canvas_release(self: Any, event: tk.Event) -> None:
        editing = bool(getattr(self, "crop_editing", False))
        original_on_canvas_release(self, event)
        if editing:
            self._record_history(force=True, kind="crop")

    def toggle_crop_editing(self: Any) -> None:
        was_editing = bool(getattr(self, "crop_editing", False))
        original_toggle_crop_editing(self)
        if was_editing and not bool(getattr(self, "crop_editing", False)):
            self._record_history(force=True, kind="crop")

    def reset_controls(self: Any) -> None:
        original_reset_controls(self)
        self._record_history(force=True, kind="reset")

    def sync_controls_selected(self: Any) -> None:
        indices = self.selected_indices()
        original_sync_controls_selected(self)
        self._record_history(force=True, kind="sync-controls", indices=indices)

    def sync_crop_selected(self: Any) -> None:
        indices = self.selected_indices()
        original_sync_crop_selected(self)
        self._record_history(force=True, kind="sync-crop", indices=indices)

    app_class._build_ui = build_ui
    app_class._configure_direct_base_panel = configure_direct_base_panel
    app_class._add_neutral_gain_panel = add_neutral_gain_panel
    app_class._add_history_buttons = add_history_buttons
    app_class._bind_history_shortcuts = bind_history_shortcuts
    app_class._detected_base = detected_base
    app_class._direct_base_units = direct_base_units
    app_class._set_direct_base_units = set_direct_base_units
    app_class.controls_value = controls_value
    app_class.apply_controls = apply_controls
    app_class.update_base_value_text = update_base_value_text
    app_class.commit_base_entry = commit_base_entry
    app_class.adjust_base = adjust_base
    app_class.reset_base_adjust = reset_base_adjust
    app_class.reset_neutral_gains = reset_neutral_gains
    app_class._item_key = item_key
    app_class._item_snapshot = item_snapshot
    app_class._history_for = history_for
    app_class._record_history = record_history
    app_class._restore_snapshot = restore_snapshot
    app_class.undo_edit = undo_edit
    app_class.redo_edit = redo_edit
    app_class._update_history_buttons = update_history_buttons
    app_class.load_index = load_index
    app_class._control_changed = control_changed
    app_class.auto_analyze = auto_analyze
    app_class._apply_pick = apply_pick
    app_class.on_canvas_release = on_canvas_release
    app_class.toggle_crop_editing = toggle_crop_editing
    app_class.reset_controls = reset_controls
    app_class.sync_controls_selected = sync_controls_selected
    app_class.sync_crop_selected = sync_crop_selected
    app_class._v054_history_direct_applied = True

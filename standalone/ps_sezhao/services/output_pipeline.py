from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..engine import Analysis, Controls
from .output_service import (
    ExportEvent,
    ExportSummary,
    ExportTask,
    OutputQueueService,
    reserve_unique_destination,
)


OUTPUT_BUTTON_TEXTS = {
    "保存当前",
    "导出选中",
    "导出全部",
    "LR 批量应用并完成",
}


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def apply_output_pipeline(app_class: Type[Any]) -> None:
    """Attach cancellable full-resolution export queue to the desktop UI."""

    if getattr(app_class, "_output_pipeline_applied", False):
        return

    original_init = app_class.__init__
    original_build_variables = app_class._build_variables
    original_build_controls_panel = app_class._build_controls_panel

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.export_progress = tk.DoubleVar(value=0.0)
        self.export_queue_status = tk.StringVar(value="输出队列空闲")

    def init(
        self: Any,
        root: Any,
        *,
        lr_job: str | None = None,
        initial_files: list[str] | None = None,
    ) -> None:
        self._output_service = OutputQueueService()
        self._active_export_batch: str | None = None
        self._output_closed = False
        self._output_action_buttons: list[ttk.Button] = []
        self.export_cancel_button: ttk.Button | None = None
        original_init(self, root, lr_job=lr_job, initial_files=initial_files)
        self.root.bind("<Destroy>", self._output_destroy_event, add="+")

    def build_controls_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_controls_panel(self, parent)
        fixed = next(
            (
                child
                for child in parent.winfo_children()
                if isinstance(child, ttk.LabelFrame)
                and str(child.cget("text")) == "输出（固定）"
            ),
            None,
        )
        if fixed is None:
            return

        ttk.Separator(fixed, orient="horizontal").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 6),
        )
        queue_frame = ttk.Frame(fixed)
        queue_frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        queue_frame.columnconfigure(0, weight=1)
        ttk.Progressbar(
            queue_frame,
            variable=self.export_progress,
            maximum=100.0,
            mode="determinate",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.export_cancel_button = ttk.Button(
            queue_frame,
            text="取消导出",
            command=self.cancel_export,
            state="disabled",
        )
        self.export_cancel_button.grid(row=0, column=1, sticky="e")
        ttk.Label(
            fixed,
            textvariable=self.export_queue_status,
            foreground="#666",
            wraplength=295,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(5, 0))

        self._output_action_buttons = []
        for widget in _walk_widgets(fixed):
            if not isinstance(widget, ttk.Button):
                continue
            try:
                text = str(widget.cget("text"))
            except tk.TclError:
                continue
            if text in OUTPUT_BUTTON_TEXTS:
                self._output_action_buttons.append(widget)

    def output_destroy_event(self: Any, event: Any) -> None:
        if getattr(event, "widget", None) is self.root:
            self._shutdown_output_pipeline()

    def shutdown_output_pipeline(self: Any) -> None:
        if self._output_closed:
            return
        self._output_closed = True
        self._output_service.shutdown()

    def set_output_busy(self: Any, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in self._output_action_buttons:
            try:
                button.configure(state=state)
            except tk.TclError:
                pass
        if self.export_cancel_button is not None:
            try:
                self.export_cancel_button.configure(state="normal" if busy else "disabled")
            except tk.TclError:
                pass

    def submit_export_tasks(self: Any, tasks: list[ExportTask]) -> None:
        if not tasks:
            return
        if self._active_export_batch is not None:
            messagebox.showinfo("正在导出", "当前输出任务尚未完成。可先取消，或等待任务结束。")
            return

        self.export_progress.set(0.0)
        self.export_queue_status.set(f"准备导出 {len(tasks)} 张图片…")
        self.status.set(f"准备导出 {len(tasks)} 张图片…")
        self._set_output_busy(True)

        def on_event(event: ExportEvent) -> None:
            try:
                self.root.after(0, lambda value=event: self._handle_export_event(value))
            except (RuntimeError, tk.TclError):
                pass

        def on_complete(summary: ExportSummary) -> None:
            try:
                self.root.after(0, lambda value=summary: self._handle_export_complete(value))
            except (RuntimeError, tk.TclError):
                pass

        try:
            batch_id = self._output_service.submit(
                tasks,
                on_event=on_event,
                on_complete=on_complete,
            )
        except Exception as exc:
            self._set_output_busy(False)
            self.export_queue_status.set("无法启动输出任务。")
            messagebox.showerror("无法开始导出", str(exc))
            return
        self._active_export_batch = batch_id

    def handle_export_event(self: Any, event: ExportEvent) -> None:
        if self._active_export_batch not in {None, event.batch_id}:
            return
        self.export_progress.set(min(100.0, max(0.0, event.overall_progress * 100.0)))
        if event.message:
            self.export_queue_status.set(event.message)
            self.status.set(event.message)

    def handle_export_complete(self: Any, summary: ExportSummary) -> None:
        if self._active_export_batch not in {None, summary.batch_id}:
            return
        self._active_export_batch = None
        self._set_output_busy(False)

        if summary.cancelled:
            progress = 100.0 * summary.completed / max(1, summary.total)
            self.export_progress.set(progress)
            message = (
                f"导出已停止：成功 {summary.succeeded}，失败 {summary.failed}，"
                f"未处理 {summary.cancelled}。"
            )
        else:
            self.export_progress.set(100.0)
            message = f"导出完成：成功 {summary.succeeded}，失败 {summary.failed}。"
        self.export_queue_status.set(message)
        self.status.set(message)

        if summary.failures:
            details = "\n".join(
                f"{failure.index}. {Path(failure.source).name}：{failure.error}"
                for failure in summary.failures[:8]
            )
            if len(summary.failures) > 8:
                details += f"\n……另有 {len(summary.failures) - 8} 个错误。"
            messagebox.showwarning(
                "部分图片导出失败",
                f"{message}\n\n失败详情：\n{details}",
            )

    def cancel_export(self: Any) -> None:
        batch_id = self._active_export_batch
        if batch_id is None:
            return
        if self._output_service.cancel(batch_id):
            self.export_queue_status.set("正在取消；当前解码或处理分块结束后停止…")
            self.status.set("正在取消输出任务…")
            if self.export_cancel_button is not None:
                self.export_cancel_button.configure(state="disabled")

    def task_for_item(self: Any, item: Any, destination: Path) -> ExportTask:
        analysis = Analysis.from_dict(item.analysis) if item.analysis else None
        output = (
            self._output_settings_for_item(item)
            if hasattr(self, "_output_settings_for_item")
            else {
                "format_label": self.output_format_label.get(),
                "jpeg_quality": self._output_quality(),
            }
        )
        format_label = str(output.get("format_label") or self.output_format_label.get())
        formats = getattr(__import__("ps_sezhao.app_v057_rotate_output_patch", fromlist=["OUTPUT_FORMATS"]), "OUTPUT_FORMATS")
        _extension, bit_depth, _format_name = formats.get(format_label, self._output_spec())
        try:
            quality = min(100, max(1, int(output.get("jpeg_quality", 95))))
        except (TypeError, ValueError):
            quality = 95
        raw_settings = (
            self._raw_settings_for_item(item)
            if hasattr(self, "_raw_settings_for_item")
            else self._raw_settings_snapshot(item)
            if hasattr(self, "_raw_settings_snapshot")
            else self.raw_settings_value()
            if hasattr(self, "raw_settings_value")
            else None
        )
        return ExportTask(
            source=Path(item.path),
            destination=Path(destination),
            controls=Controls.from_dict(item.controls),
            crop=tuple(item.crop),
            rotation=int(getattr(item, "rotation", 0)),
            geometry=dict(getattr(item, "geometry", {}) or {}),
            analysis=analysis,
            raw_settings=raw_settings,
            bit_depth=bit_depth,
            jpeg_quality=quality,
            label=Path(item.path).name,
        )

    def save_current(self: Any) -> None:
        item = self.current_item()
        if item is None:
            return
        self._store_current_state()
        output = self._output_settings_for_item(item) if hasattr(self, "_output_settings_for_item") else {}
        format_label = str(output.get("format_label") or self.output_format_label.get())
        formats = getattr(__import__("ps_sezhao.app_v057_rotate_output_patch", fromlist=["OUTPUT_FORMATS"]), "OUTPUT_FORMATS")
        extension, _bit_depth, format_name = formats.get(format_label, self._output_spec())
        target = filedialog.asksaveasfilename(
            title="保存正片",
            initialfile=item.path.stem + "_PS-Sezhao" + extension,
            defaultextension=extension,
            filetypes=[(format_name, "*" + extension), ("全部文件", "*.*")],
        )
        if not target:
            return
        self._submit_export_tasks([self._task_for_item(item, Path(target))])

    def batch_export(self: Any, indices: list[int]) -> None:
        if not indices:
            return
        if self.lr_job_data is not None:
            self._run_lr_job()
            return
        self._store_current_state()
        destination = filedialog.askdirectory(title="选择批量输出文件夹")
        if not destination:
            return

        output_dir = Path(destination)
        reserved: set[str] = set()
        tasks: list[ExportTask] = []
        formats = getattr(__import__("ps_sezhao.app_v057_rotate_output_patch", fromlist=["OUTPUT_FORMATS"]), "OUTPUT_FORMATS")
        for index in indices:
            if index < 0 or index >= len(self.items):
                continue
            item = self.items[index]
            output = self._output_settings_for_item(item) if hasattr(self, "_output_settings_for_item") else {}
            format_label = str(output.get("format_label") or self.output_format_label.get())
            extension = formats.get(format_label, self._output_spec())[0]
            requested = output_dir / f"{item.path.stem}_PS-Sezhao{extension}"
            target = reserve_unique_destination(requested, reserved)
            tasks.append(self._task_for_item(item, target))
        self._submit_export_tasks(tasks)

    app_class._build_variables = build_variables
    app_class.__init__ = init
    app_class._build_controls_panel = build_controls_panel
    app_class._output_destroy_event = output_destroy_event
    app_class._shutdown_output_pipeline = shutdown_output_pipeline
    app_class._set_output_busy = set_output_busy
    app_class._submit_export_tasks = submit_export_tasks
    app_class._handle_export_event = handle_export_event
    app_class._handle_export_complete = handle_export_complete
    app_class.cancel_export = cancel_export
    app_class._task_for_item = task_for_item
    app_class.save_current = save_current
    app_class._batch_export = batch_export
    app_class._output_pipeline_applied = True

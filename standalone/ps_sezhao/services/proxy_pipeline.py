from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from typing import Any, Type

import tkinter as tk
from tkinter import filedialog, messagebox

from ..core.geometry import apply_photo_geometry
from ..engine import Analysis, Controls
from ..io_utils import load_image
from ..raw_io import is_raw_path, prepare_display_output, raw_runtime_summary
from ..workspace import clamp_crop, rotate_array
from .proxy_service import PreviewFrame, PreviewProxyService

IMPORT_THUMBNAIL_PREFETCH_LIMIT = 16


def apply_proxy_pipeline(app_class: Type[Any]) -> None:
    """Use thumbnail -> edit proxy -> full-resolution-on-output loading."""

    if getattr(app_class, "_proxy_pipeline_applied", False):
        return

    original_init = app_class.__init__
    original_open_paths = app_class.open_paths
    original_clear_current_display = app_class._clear_current_display
    original_reload_current_raw = getattr(app_class, "reload_current_raw", None)

    def init(
        self: Any,
        root: Any,
        *,
        lr_job: str | None = None,
        initial_files: list[str] | None = None,
    ) -> None:
        self._proxy_service = PreviewProxyService()
        self._proxy_generation = 0
        self._proxy_closed = False
        original_init(self, root, lr_job=lr_job, initial_files=initial_files)
        self.root.bind("<Destroy>", self._proxy_destroy_event, add="+")

    def proxy_destroy_event(self: Any, event: Any) -> None:
        if getattr(event, "widget", None) is self.root:
            self._shutdown_proxy_pipeline()

    def shutdown_proxy_pipeline(self: Any) -> None:
        if self._proxy_closed:
            return
        self._proxy_closed = True
        self._proxy_generation += 1
        self._proxy_service.shutdown()

    def raw_settings_snapshot(self: Any, item: Any | None = None) -> Any:
        if item is not None and hasattr(self, "_raw_settings_for_item"):
            return self._raw_settings_for_item(item)
        return self.raw_settings_value() if hasattr(self, "raw_settings_value") else None

    def dispatch_future(
        self: Any,
        future: Future[PreviewFrame],
        success: Any,
        failure: Any | None = None,
    ) -> None:
        def done(completed: Future[PreviewFrame]) -> None:
            try:
                frame = completed.result()
            except Exception as exc:
                if failure is None:
                    return
                try:
                    self.root.after(0, lambda error=exc: failure(error))
                except (RuntimeError, tk.TclError):
                    return
            else:
                try:
                    self.root.after(0, lambda value=frame: success(value))
                except (RuntimeError, tk.TclError):
                    return

        future.add_done_callback(done)

    def open_paths(self: Any, paths: list[Path], *, replace: bool = False) -> None:
        previous = {str(item.path.expanduser().resolve(strict=False)) for item in self.items}
        original_open_paths(self, paths, replace=replace)
        new_items = [
            item
            for item in self.items
            if str(item.path.expanduser().resolve(strict=False)) not in previous
        ]
        for item in new_items[:IMPORT_THUMBNAIL_PREFETCH_LIMIT]:
            self._proxy_service.request_thumbnail(
                item.path,
                self._raw_settings_snapshot(item),
            )

    def prepare_index_ui(self: Any, index: int) -> None:
        item = self.items[index]
        self._loading_item = True
        try:
            if hasattr(self, "_invalidate_render"):
                self._invalidate_render()
            else:
                self.render_generation += 1
            self.current_index = index
            self.full_image = None
            self.preview_source = None
            self.preview_result = None
            self.metadata = {}
            self.crop_norm = clamp_crop(item.crop)
            self.analysis = Analysis.from_dict(item.analysis) if item.analysis else None
            self.apply_controls(Controls.from_dict(item.controls))
            self.canvas.delete("all")
            self._tree_updating = True
            try:
                self.file_tree.selection_add(str(index))
                self.file_tree.focus(str(index))
                self.file_tree.see(str(index))
            finally:
                self._tree_updating = False
            self._update_crop_status()
            if hasattr(self, "rotation_status"):
                self.rotation_status.set(f"旋转：{int(item.rotation) % 360}°")
            if hasattr(self, "raw_info") and is_raw_path(item.path):
                self.raw_info.set(f"{raw_runtime_summary()} · 正在生成编辑代理")
        finally:
            self._loading_item = False

    def load_index(self: Any, index: int) -> None:
        if index < 0 or index >= len(self.items):
            return
        self._store_current_state()
        self._proxy_generation += 1
        generation = self._proxy_generation
        if hasattr(self, "raw_decode_generation"):
            self.raw_decode_generation += 1
        item = self.items[index]
        settings = self._raw_settings_snapshot(item)
        self._prepare_proxy_index_ui(index)
        self.status.set(f"正在读取轻量缩略图：{item.path.name}…")

        thumbnail = self._proxy_service.request_thumbnail(item.path, settings)
        proxy = self._proxy_service.request_proxy(item.path, settings)
        self._dispatch_proxy_future(
            thumbnail,
            lambda frame: self._accept_proxy_thumbnail(generation, index, frame),
        )
        self._dispatch_proxy_future(
            proxy,
            lambda frame: self._accept_edit_proxy(generation, index, frame),
            lambda error: self._proxy_load_error(generation, index, error),
        )

    def accept_proxy_thumbnail(
        self: Any,
        generation: int,
        index: int,
        frame: PreviewFrame,
    ) -> None:
        if generation != self._proxy_generation or index != self.current_index:
            return
        if self.preview_source is not None:
            return
        item = self.items[index]
        shown = rotate_array(frame.image, item.rotation)
        shown = apply_photo_geometry(shown, item.geometry)
        self._set_display_image(prepare_display_output(shown, frame.metadata))
        self.zoom_fit_view()
        source = frame.metadata.get("thumbnail_source", "thumbnail")
        self.status.set(f"已显示轻量缩略图（{source}）；正在生成高质量编辑代理…")

    def accept_edit_proxy(
        self: Any,
        generation: int,
        index: int,
        frame: PreviewFrame,
    ) -> None:
        if generation != self._proxy_generation or index != self.current_index:
            return
        item = self.items[index]
        self.full_image = None
        rotated = rotate_array(frame.image, item.rotation)
        self.preview_source = apply_photo_geometry(rotated, item.geometry)
        self.preview_result = None
        self.metadata = dict(frame.metadata)
        self.metadata["geometry_applied"] = True
        self.crop_norm = clamp_crop(item.crop)
        self.analysis = Analysis.from_dict(item.analysis) if item.analysis else None
        self._set_display_image(prepare_display_output(self.preview_source, self.metadata))
        self.zoom_fit_view()
        self._update_crop_status()
        self._update_tree_row(index)

        if hasattr(self, "raw_info") and is_raw_path(item.path):
            size = self.metadata.get("raw_size") or {}
            dimensions = f"{size.get('width', self.preview_source.shape[1])}×{size.get('height', self.preview_source.shape[0])}"
            self.raw_info.set(
                f"{self.metadata.get('raw_runtime', raw_runtime_summary())} · {dimensions} · 编辑代理"
            )

        if self.analysis is None:
            self.auto_analyze()
        else:
            self.status.set(f"高质量编辑代理已就绪：{item.path.name}")
            self.schedule_render(0)
        self._prefetch_next_proxy(index)

    def prefetch_next_proxy(self: Any, index: int) -> None:
        next_index = index + 1
        if next_index >= len(self.items):
            return
        item = self.items[next_index]
        settings = self._raw_settings_snapshot(item)
        self._proxy_service.request_thumbnail(item.path, settings)
        self._proxy_service.request_proxy(item.path, settings)

    def proxy_load_error(self: Any, generation: int, index: int, error: Exception) -> None:
        if generation != self._proxy_generation or index != self.current_index:
            return
        item = self.items[index]
        self.status.set("编辑代理读取失败。")
        if hasattr(self, "raw_info") and is_raw_path(item.path):
            self.raw_info.set(raw_runtime_summary())
        title = "无法打开相机 RAW" if is_raw_path(item.path) else "无法打开图像"
        messagebox.showerror(title, str(error))

    def reload_current_raw(self: Any) -> None:
        item = self.current_item()
        if item is None or not is_raw_path(item.path):
            if original_reload_current_raw is not None:
                original_reload_current_raw(self)
            return
        if hasattr(self, "raw_settings_value"):
            item.raw_settings = self.raw_settings_value().to_dict()
        self._proxy_service.invalidate(item.path)
        item.analysis = None
        self.analysis = None
        assert self.current_index is not None
        self.load_index(self.current_index)

    def save_current(self: Any) -> None:
        item = self.current_item()
        if item is None or self.analysis is None or self.preview_source is None:
            messagebox.showinfo("尚未就绪", "请等待当前图片的高质量编辑代理与基底分析完成。")
            return
        self._store_current_state()
        extension, _bit_depth, format_name = self._output_spec()
        default_name = item.path.stem + "_PS-Sezhao" + extension
        target = filedialog.asksaveasfilename(
            title="保存正片",
            initialfile=default_name,
            defaultextension=extension,
            filetypes=[(format_name, "*" + extension), ("全部文件", "*.*")],
        )
        if not target:
            return

        path = Path(item.path)
        destination = Path(target)
        rotation = int(item.rotation)
        crop = tuple(self.crop_norm)
        geometry = dict(item.geometry)
        analysis = self.analysis
        controls = self.controls_value()
        settings = self._raw_settings_snapshot(item)
        self.status.set(f"正在读取全分辨率原图：{item.path.name}…")

        def worker() -> None:
            try:
                image, metadata = load_image(path, raw_settings=settings)
                image = rotate_array(image, rotation)
                image = apply_photo_geometry(image, geometry)
                self.root.after(
                    0,
                    lambda: self._process_and_save(
                        image,
                        destination,
                        analysis,
                        controls,
                        crop,
                        metadata,
                    ),
                )
            except Exception as exc:
                try:
                    self.root.after(
                        0,
                        lambda message=str(exc): messagebox.showerror("保存失败", message),
                    )
                except (RuntimeError, tk.TclError):
                    return

        import threading

        threading.Thread(target=worker, daemon=True).start()

    def clear_current_display(self: Any) -> None:
        self._proxy_generation += 1
        original_clear_current_display(self)

    app_class.__init__ = init
    app_class.open_paths = open_paths
    app_class.load_index = load_index
    app_class._prepare_proxy_index_ui = prepare_index_ui
    app_class._dispatch_proxy_future = dispatch_future
    app_class._accept_proxy_thumbnail = accept_proxy_thumbnail
    app_class._accept_edit_proxy = accept_edit_proxy
    app_class._prefetch_next_proxy = prefetch_next_proxy
    app_class._proxy_load_error = proxy_load_error
    app_class._raw_settings_snapshot = raw_settings_snapshot
    app_class._proxy_destroy_event = proxy_destroy_event
    app_class._shutdown_proxy_pipeline = shutdown_proxy_pipeline
    if original_reload_current_raw is not None:
        app_class.reload_current_raw = reload_current_raw
    app_class.save_current = save_current
    app_class._clear_current_display = clear_current_display
    app_class._proxy_pipeline_applied = True

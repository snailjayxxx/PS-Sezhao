from __future__ import annotations

from pathlib import Path
from typing import Any, Type

from ..storage.paths import default_project_database_path
from ..storage.project_store import ProjectStore, normalized_file_path


SAVE_DELAY_MS = 650


def apply_project_session(app_class: Type[Any]) -> None:
    """Attach recoverable workspace save/restore to the configured UI class."""

    if getattr(app_class, "_project_session_applied", False):
        return

    original_init = app_class.__init__
    original_store_current_state = app_class._store_current_state
    original_load_index = app_class.load_index

    def init(
        self: Any,
        root: Any,
        *,
        lr_job: str | None = None,
        initial_files: list[str] | None = None,
    ) -> None:
        self.project_store = ProjectStore(default_project_database_path())
        self._project_persistence_enabled = lr_job is None
        self._project_restoring = False
        self._project_save_after = None
        self._project_loaded_paths: set[str] = set()

        original_init(self, root, lr_job=lr_job, initial_files=initial_files)
        self.root.protocol("WM_DELETE_WINDOW", self._close_with_project_save)

        if (
            self._project_persistence_enabled
            and not initial_files
            and not self.items
            and not getattr(self, "_roll_restore_pending", False)
        ):
            self._restore_project_session()

    def store_current_state(self: Any) -> None:
        original_store_current_state(self)
        self._schedule_project_save()

    def load_index(self: Any, index: int) -> None:
        if 0 <= index < len(self.items) and not getattr(self, "_roll_project_loading", False):
            item = self.items[index]
            key = normalized_file_path(item.path)
            if key not in self._project_loaded_paths:
                self._project_loaded_paths.add(key)
                try:
                    saved = self.project_store.load_image_state(item.path)
                except Exception:
                    saved = None
                if saved is not None:
                    item.controls = dict(saved.controls)
                    item.analysis = None if saved.analysis is None else dict(saved.analysis)
                    item.crop = tuple(saved.crop)
                    item.rotation = int(saved.rotation)
                    item.geometry = dict(saved.geometry)
                    item.raw_settings = dict(saved.raw_settings)
                    item.output_settings = dict(saved.output_settings)
        original_load_index(self, index)

    def schedule_project_save(self: Any) -> None:
        if not self._project_persistence_enabled or self._project_restoring:
            return
        pending = self._project_save_after
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass
        self._project_save_after = self.root.after(SAVE_DELAY_MS, self._save_project_session_now)

    def save_project_session_now(self: Any) -> None:
        self._project_save_after = None
        if not self._project_persistence_enabled or self._project_restoring:
            return

        original_store_current_state(self)
        current = self.current_item()
        image_states = [
            {
                "file_path": item.path,
                "controls": dict(item.controls),
                "analysis": None if item.analysis is None else dict(item.analysis),
                "crop": tuple(item.crop),
                "rotation": int(getattr(item, "rotation", 0)),
                "geometry": dict(getattr(item, "geometry", {}) or {}),
                "raw_settings": dict(getattr(item, "raw_settings", {}) or {}),
                "output_settings": dict(getattr(item, "output_settings", {}) or {}),
            }
            for item in self.items
        ]
        try:
            self.project_store.save_session(
                image_states=image_states,
                file_paths=[item.path for item in self.items],
                current_file=None if current is None else current.path,
            )
        except Exception as exc:
            self.status.set(f"自动保存工作状态失败：{exc}")

    def restore_project_session(self: Any) -> None:
        if not self._project_persistence_enabled:
            return
        try:
            workspace = self.project_store.load_workspace()
        except Exception as exc:
            self.status.set(f"读取上次工作状态失败：{exc}")
            return

        paths = [Path(path) for path in workspace.file_paths if Path(path).is_file()]
        if not paths:
            return

        self._project_restoring = True
        try:
            self.open_paths(paths, replace=True)
            if workspace.current_file:
                active = normalized_file_path(workspace.current_file)
                for index, item in enumerate(self.items):
                    if normalized_file_path(item.path) == active:
                        if index != self.current_index:
                            self.load_index(index)
                        break
            self.status.set(f"已恢复上次工作状态，共 {len(self.items)} 张图片。")
        except Exception as exc:
            self.status.set(f"恢复上次工作状态失败：{exc}")
        finally:
            self._project_restoring = False

    def close_with_project_save(self: Any) -> None:
        pending = self._project_save_after
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass
            self._project_save_after = None
        try:
            self._save_project_session_now()
        finally:
            self.root.destroy()

    app_class.__init__ = init
    app_class._store_current_state = store_current_state
    app_class.load_index = load_index
    app_class._schedule_project_save = schedule_project_save
    app_class._save_project_session_now = save_project_session_now
    app_class._restore_project_session = restore_project_session
    app_class._close_with_project_save = close_with_project_save
    app_class._project_session_applied = True

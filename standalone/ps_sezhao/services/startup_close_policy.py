from __future__ import annotations

from datetime import date
from typing import Any, Type

from tkinter import messagebox, simpledialog

from ..core.roll_project import RollProjectSettings, assign_project_output_settings
from ..storage.roll_project_store import RollProjectStore


def apply_startup_close_policy(app_class: Type[Any]) -> None:
    """Start with an empty workspace and make project saving an explicit close action."""

    if getattr(app_class, "_startup_close_policy_applied", False):
        return

    original_init = app_class.__init__

    def init(
        self: Any,
        root: Any,
        *,
        lr_job: str | None = None,
        initial_files: list[str] | None = None,
    ) -> None:
        # The roll-project layer asks its store for the previously active project
        # before the base window opens any explicitly supplied files. Temporarily
        # report no active project so a file opened from Finder never inherits a
        # previous roll's metadata. The transient workspace restore is also
        # suppressed for this initialization only.
        original_get_active_project_id = RollProjectStore.get_active_project_id
        RollProjectStore.get_active_project_id = lambda _store: None
        self._restore_project_session = lambda: None
        self._restore_active_roll_project = lambda: None
        try:
            original_init(self, root, lr_job=lr_job, initial_files=initial_files)
        finally:
            RollProjectStore.get_active_project_id = original_get_active_project_id
            self.__dict__.pop("_restore_project_session", None)
            self.__dict__.pop("_restore_active_roll_project", None)

        self._roll_restore_pending = False
        if lr_job is None:
            self.active_roll_project_id = None
            self.active_roll_project_name = ""
            self.active_roll_project_settings = RollProjectSettings()
            self.active_roll_output_preset_id = None
            try:
                self.roll_project_store.set_active_project(None)
            except Exception:
                pass
            try:
                self.project_store.clear_workspace()
            except Exception:
                pass
            if hasattr(self, "_refresh_roll_project_status"):
                self._refresh_roll_project_status()
            if initial_files:
                self.status.set(f"已打开 {len(self.items)} 张图片，当前为未保存的临时工作区。")
            else:
                self.status.set("请选择图像或打开已有胶卷项目。")

        self.root.protocol("WM_DELETE_WINDOW", self._close_with_project_prompt)

    def cancel_pending_workspace_save(self: Any) -> None:
        pending = getattr(self, "_project_save_after", None)
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass
            self._project_save_after = None

    def clear_transient_workspace(self: Any) -> None:
        try:
            self.project_store.clear_workspace()
        except Exception:
            pass
        try:
            self.roll_project_store.set_active_project(None)
        except Exception:
            pass

    def save_temporary_roll_for_close(self: Any) -> bool:
        default_name = f"胶卷 {date.today().isoformat()}"
        name = simpledialog.askstring(
            "保存胶卷项目",
            "请输入胶卷项目名称：",
            initialvalue=default_name,
            parent=self.root,
        )
        if name is None:
            return False
        cleaned_name = " ".join(name.split())
        if not cleaned_name:
            messagebox.showwarning("无法保存", "胶卷项目名称不能为空。", parent=self.root)
            return False

        settings = RollProjectSettings(
            roll_name=cleaned_name,
            capture_date=date.today().isoformat(),
        ).sanitized()
        try:
            project_id = self.roll_project_store.create_project(
                cleaned_name,
                shared=settings.to_dict(),
                make_active=True,
            )
            self.active_roll_project_id = project_id
            self.active_roll_project_name = cleaned_name
            self.active_roll_project_settings = settings
            self.active_roll_output_preset_id = None
            assign_project_output_settings(
                self.items,
                settings,
                overwrite_common=False,
                renumber_all=True,
            )
            self._store_current_state()
            self._save_active_roll_project()
        except Exception as exc:
            messagebox.showerror("保存胶卷项目失败", str(exc), parent=self.root)
            return False
        return True

    def close_with_project_prompt(self: Any) -> None:
        self._cancel_pending_workspace_save()

        if self.items:
            project_name = (
                self.active_roll_project_name
                if getattr(self, "active_roll_project_id", None)
                else "当前照片"
            )
            decision = messagebox.askyesnocancel(
                "关闭 PS-Sezhao",
                f"是否保存“{project_name}”这次的胶卷项目？\n\n"
                "选择“是”保存后关闭；选择“否”直接关闭；选择“取消”返回程序。",
                parent=self.root,
            )
            if decision is None:
                return
            if decision:
                if getattr(self, "active_roll_project_id", None):
                    try:
                        self._store_current_state()
                        self._save_active_roll_project()
                    except Exception as exc:
                        messagebox.showerror("保存胶卷项目失败", str(exc), parent=self.root)
                        return
                elif not self._save_temporary_roll_for_close():
                    return

        self._clear_transient_workspace()
        self.root.destroy()

    app_class.__init__ = init
    app_class._cancel_pending_workspace_save = cancel_pending_workspace_save
    app_class._clear_transient_workspace = clear_transient_workspace
    app_class._save_temporary_roll_for_close = save_temporary_roll_for_close
    app_class._close_with_project_prompt = close_with_project_prompt
    app_class._startup_close_policy_applied = True

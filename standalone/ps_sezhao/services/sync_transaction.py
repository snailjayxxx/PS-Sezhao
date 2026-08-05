from __future__ import annotations

from typing import Any, Type

from tkinter import messagebox

from .sync_pipeline import MODULE_LABELS, copy_modules


def apply_sync_transaction_guard(app_class: Type[Any]) -> None:
    """Apply selected modules to all targets or roll the complete change back."""

    if getattr(app_class, "_sync_transaction_guard_applied", False):
        return

    def apply_sync_dialog(
        self: Any,
        dialog: Any,
        variables: dict[str, Any],
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

        valid_targets = [index for index in targets if 0 <= index < len(self.items)]
        originals = {index: self.items[index] for index in valid_targets}
        try:
            replacements = {
                index: copy_modules(source, self.items[index], modules)
                for index in valid_targets
            }
            for index in valid_targets:
                if hasattr(self, "_history_for"):
                    self._history_for(index)
            for index, replacement in replacements.items():
                self.items[index] = replacement
            for index in valid_targets:
                self._update_tree_row(index)
            if hasattr(self, "_record_history"):
                self._record_history(force=True, kind="sync-modules", indices=valid_targets)
            if hasattr(self, "_save_project_session_now"):
                self._save_project_session_now()
            elif hasattr(self, "_schedule_project_save"):
                self._schedule_project_save()
        except Exception as exc:
            for index, original in originals.items():
                self.items[index] = original
                try:
                    self._update_tree_row(index)
                except Exception:
                    pass
            messagebox.showerror(
                "复制设置失败",
                f"所有目标图片均已恢复到修改前状态。\n\n{exc}",
                parent=dialog,
            )
            return

        names = "、".join(MODULE_LABELS[key] for key in MODULE_LABELS if key in modules)
        self.status.set(f"已将 {names} 复制到 {len(valid_targets)} 张图片。")
        dialog.destroy()

    app_class._apply_sync_dialog = apply_sync_dialog
    app_class._sync_transaction_guard_applied = True

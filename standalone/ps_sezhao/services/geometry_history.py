from __future__ import annotations

from typing import Any, Type


def apply_geometry_history_guard(app_class: Type[Any]) -> None:
    """Prevent transient geometry refreshes from creating undo entries."""

    if getattr(app_class, "_geometry_history_guard_applied", False):
        return

    original_refresh = app_class._refresh_geometry_preview
    original_restore = getattr(app_class, "restore_snapshot", None)
    original_rotate = getattr(app_class, "rotate_current", None)
    original_cancel_perspective = app_class._cancel_perspective_mode

    def refresh_geometry_preview(self: Any) -> None:
        item = self.current_item()
        if item is None or self.current_index is None:
            return
        self._store_current_state()
        suppress = bool(getattr(self, "_suppress_geometry_history", False))
        restoring = bool(getattr(self, "_history_restoring", False))
        transient = bool(getattr(self, "_perspective_editing", False))
        if not suppress and not restoring and not transient and hasattr(self, "_record_history"):
            self._record_history(force=True, kind="geometry")
        self._update_tree_row(self.current_index)
        index = self.current_index
        self.load_index(index)
        if hasattr(self, "_schedule_project_save"):
            self._schedule_project_save()

    def restore_snapshot(self: Any, snapshot: dict[str, Any]) -> None:
        self._suppress_geometry_history = True
        try:
            if original_restore is not None:
                original_restore(self, snapshot)
        finally:
            self._suppress_geometry_history = False

    def rotate_current(self: Any, clockwise_degrees: int) -> None:
        self._suppress_geometry_history = True
        try:
            if original_rotate is not None:
                original_rotate(self, clockwise_degrees)
        finally:
            self._suppress_geometry_history = False

    def cancel_perspective_mode(self: Any, *, restore: bool) -> None:
        self._suppress_geometry_history = True
        try:
            original_cancel_perspective(self, restore=restore)
        finally:
            self._suppress_geometry_history = False

    app_class._refresh_geometry_preview = refresh_geometry_preview
    if original_restore is not None:
        app_class.restore_snapshot = restore_snapshot
        app_class._restore_snapshot = restore_snapshot
    if original_rotate is not None:
        app_class.rotate_current = rotate_current
    app_class._cancel_perspective_mode = cancel_perspective_mode
    app_class._geometry_history_guard_applied = True

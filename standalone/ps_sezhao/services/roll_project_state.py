from __future__ import annotations

from typing import Any, Type

from ..core.roll_project import assign_project_output_settings


def apply_roll_project_state_guard(app_class: Type[Any]) -> None:
    """Keep project metadata and frame numbers complete before persistence."""

    if getattr(app_class, "_roll_project_state_guard_applied", False):
        return

    original_store_current_state = app_class._store_current_state
    original_save_active_roll_project = app_class._save_active_roll_project

    def complete_project_output_state(self: Any, *, update_ui: bool) -> None:
        if not getattr(self, "active_roll_project_id", None):
            return
        assign_project_output_settings(
            self.items,
            self.active_roll_project_settings,
            overwrite_common=False,
            renumber_all=False,
        )
        current = self.current_item()
        if (
            update_ui
            and current is not None
            and not getattr(self, "_roll_project_loading", False)
            and not getattr(self, "_loading_item", False)
            and hasattr(self, "_apply_output_settings_to_ui")
        ):
            self._apply_output_settings_to_ui(current.output_settings)

    def store_current_state(self: Any) -> None:
        # Project restoration first creates list rows and then replaces their
        # temporary defaults with database states. A same-index load performed
        # during that interval must never write the temporary UI values back
        # over the restored controls.
        if getattr(self, "_roll_project_loading", False):
            return
        # Older output layers write the visible controls first. Complete any
        # missing project metadata afterwards so an empty frame-number control
        # cannot erase the number assigned by the active roll project.
        original_store_current_state(self)
        self._complete_project_output_state(update_ui=True)

    def save_active_roll_project(self: Any) -> None:
        self._complete_project_output_state(update_ui=True)
        original_save_active_roll_project(self)

    app_class._complete_project_output_state = complete_project_output_state
    app_class._store_current_state = store_current_state
    app_class._save_active_roll_project = save_active_roll_project
    app_class._roll_project_state_guard_applied = True

from __future__ import annotations

from typing import Any, Type

from ..core.roll_project import assign_project_output_settings


def apply_roll_project_state_guard(app_class: Type[Any]) -> None:
    """Keep project metadata and frame numbers complete before persistence."""

    if getattr(app_class, "_roll_project_state_guard_applied", False):
        return

    original_save_active_roll_project = app_class._save_active_roll_project

    def save_active_roll_project(self: Any) -> None:
        if getattr(self, "active_roll_project_id", None):
            assign_project_output_settings(
                self.items,
                self.active_roll_project_settings,
                overwrite_common=False,
                renumber_all=False,
            )
            current = self.current_item()
            if (
                current is not None
                and not getattr(self, "_roll_project_loading", False)
                and hasattr(self, "_apply_output_settings_to_ui")
            ):
                self._apply_output_settings_to_ui(current.output_settings)
        original_save_active_roll_project(self)

    app_class._save_active_roll_project = save_active_roll_project
    app_class._roll_project_state_guard_applied = True

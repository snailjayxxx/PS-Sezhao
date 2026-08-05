from __future__ import annotations

from dataclasses import replace
from typing import Any, Type

from ..core.output import OutputSettings


def apply_safe_output_defaults(app_class: Type[Any]) -> None:
    """Use ICC preservation as the safe default for photos without saved output settings."""

    if getattr(app_class, "_safe_output_defaults_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_complete_for_item = app_class._complete_output_settings_for_item
    original_output_for_item = getattr(app_class, "_output_settings_for_item", None)
    original_load_index = app_class.load_index

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.output_color_space_label.set("保留输入 ICC")

    def complete_for_item(self: Any, item: Any) -> OutputSettings:
        settings = original_complete_for_item(self, item)
        if not getattr(item, "output_settings", None):
            return replace(settings, color_space="preserve").sanitized()
        return settings

    def output_for_item(self: Any, item: Any) -> dict[str, Any]:
        if original_output_for_item is None:
            settings = self._complete_output_settings_for_item(item)
            return settings.to_dict()
        payload = dict(original_output_for_item(self, item))
        if not getattr(item, "output_settings", None):
            payload["color_space"] = "preserve"
        return OutputSettings.from_dict(payload).to_dict()

    def load_index(self: Any, index: int) -> None:
        original_load_index(self, index)
        if 0 <= index < len(self.items) and not self.items[index].output_settings:
            self._apply_output_settings_to_ui(
                replace(self._collect_output_settings(), color_space="preserve")
            )

    app_class._build_variables = build_variables
    app_class._complete_output_settings_for_item = complete_for_item
    app_class._output_settings_for_item = output_for_item
    app_class.load_index = load_index
    app_class._safe_output_defaults_applied = True

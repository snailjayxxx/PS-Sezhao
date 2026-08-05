from __future__ import annotations

from typing import Any, Type

from ..core.output import OutputSettings
from . import sync_pipeline as sync_module


def apply_output_sync_extension(app_class: Type[Any]) -> None:
    """Keep the module-sync wrapper compatible with complete output settings."""

    if getattr(app_class, "_output_sync_extension_applied", False):
        return

    sync_module.MODULE_LABELS["output"] = "输出格式、尺寸、命名与元数据"
    original_store = app_class._store_current_state
    original_load = app_class.load_index
    original_output_for_item = getattr(app_class, "_output_settings_for_item", None)

    def output_settings_for_item(self: Any, item: Any) -> dict[str, Any]:
        if getattr(item, "output_settings", None):
            return OutputSettings.from_dict(item.output_settings).to_dict()
        if hasattr(self, "_collect_output_settings"):
            return self._collect_output_settings().to_dict()
        if original_output_for_item is not None:
            return dict(original_output_for_item(self, item))
        return OutputSettings().to_dict()

    def store_current_state(self: Any) -> None:
        original_store(self)
        item = self.current_item()
        if item is not None and hasattr(self, "_collect_output_settings"):
            item.output_settings = self._collect_output_settings().to_dict()

    def load_index(self: Any, index: int) -> None:
        original_load(self, index)
        if 0 <= index < len(self.items) and hasattr(self, "_apply_output_settings_to_ui"):
            self._apply_output_settings_to_ui(
                OutputSettings.from_dict(self.items[index].output_settings)
            )

    app_class._output_settings_for_item = output_settings_for_item
    app_class._store_current_state = store_current_state
    app_class.load_index = load_index
    app_class._output_sync_extension_applied = True

from __future__ import annotations

from typing import Any, Type


def apply_v054_sync_patch(app_class: Type[Any]) -> None:
    """Ensure multi-photo sync records a reversible state for every target."""

    if getattr(app_class, "_v054_sync_history_applied", False):
        return

    original_sync_controls = app_class.sync_controls_selected
    original_sync_crop = app_class.sync_crop_selected

    def sync_controls_selected(self: Any) -> None:
        indices = self.selected_indices()
        for index in indices:
            self._history_for(index)
        original_sync_controls(self)
        self._record_history(force=True, kind="sync-controls", indices=indices)

    def sync_crop_selected(self: Any) -> None:
        indices = self.selected_indices()
        for index in indices:
            self._history_for(index)
        original_sync_crop(self)
        self._record_history(force=True, kind="sync-crop", indices=indices)

    app_class.sync_controls_selected = sync_controls_selected
    app_class.sync_crop_selected = sync_crop_selected
    app_class._v054_sync_history_applied = True

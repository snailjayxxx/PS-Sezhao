from __future__ import annotations

from typing import Any, Type


def apply_lightroom_job_pipeline(app_class: Type[Any]) -> None:
    """Write each photo's complete edit state into Lightroom batch jobs."""

    if getattr(app_class, "_lightroom_job_pipeline_applied", False):
        return

    original_run_lr_job = getattr(app_class, "_run_lr_job", None)
    if original_run_lr_job is None:
        app_class._lightroom_job_pipeline_applied = True
        return

    def run_lr_job(self: Any) -> None:
        if self.lr_job_data is not None:
            self._store_current_state()
            job_items = self.lr_job_data.get("items") or []
            for index, job_item in enumerate(job_items):
                if index >= len(self.items):
                    break
                item = self.items[index]
                job_item["controls"] = dict(item.controls)
                job_item["analysis"] = None if item.analysis is None else dict(item.analysis)
                job_item["crop"] = list(item.crop)
                job_item["rotation"] = int(item.rotation)
                job_item["geometry"] = dict(getattr(item, "geometry", {}) or {})
                raw = (
                    self._raw_settings_for_item(item)
                    if hasattr(self, "_raw_settings_for_item")
                    else self.raw_settings_value()
                    if hasattr(self, "raw_settings_value")
                    else None
                )
                if raw is not None:
                    job_item["raw_decode"] = raw.to_dict()
                job_item["output_settings"] = dict(
                    getattr(item, "output_settings", {}) or {}
                )
        original_run_lr_job(self)

    app_class._run_lr_job = run_lr_job
    app_class._lightroom_job_pipeline_applied = True

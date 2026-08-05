from __future__ import annotations

from typing import Any

from . import complete_output_pipeline as complete_module
from . import output_service as output_module


def apply_output_queue_compatibility() -> None:
    """Route complete-output queue calls through stable output-service hooks."""

    if getattr(complete_module, "_stable_output_hooks_applied", False):
        return

    def load_image(*args: Any, **kwargs: Any) -> Any:
        return output_module.load_image(*args, **kwargs)

    def process_image_tiled(*args: Any, **kwargs: Any) -> Any:
        return output_module.process_image_tiled(*args, **kwargs)

    complete_module.load_image = load_image
    complete_module.process_image_tiled = process_image_tiled
    complete_module._stable_output_hooks_applied = True

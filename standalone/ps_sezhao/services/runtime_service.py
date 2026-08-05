from __future__ import annotations

from typing import Any

from ..processing import process_image_tiled


def install_runtime_bindings(
    *,
    app_module: Any,
    source_crop_module: Any,
    engine_module: Any,
) -> None:
    """Bind every standalone render path to the same processing functions."""

    app_module.process_image = process_image_tiled
    app_module.neutral_gains = engine_module.neutral_gains
    source_crop_module.neutral_gains = engine_module.neutral_gains

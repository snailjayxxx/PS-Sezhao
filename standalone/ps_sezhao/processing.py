from __future__ import annotations

from typing import Callable

import numpy as np

from .engine import Analysis, Controls, process_image, to_float_rgb


class ProcessingCancelled(RuntimeError):
    """Raised when a cooperative image-processing operation is cancelled."""


def process_image_tiled(
    image: np.ndarray,
    analysis: Analysis,
    controls: Controls | None = None,
    *,
    tile_rows: int = 384,
    should_cancel: Callable[[], bool] | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> np.ndarray:
    """Process a large scan in row tiles with bounded memory and cancellation."""

    rgb = to_float_rgb(image)
    height = rgb.shape[0]
    tile_rows = max(32, int(tile_rows))
    output = np.empty(rgb.shape, dtype=np.float32)

    if progress_callback is not None:
        progress_callback(0.0)
    for top in range(0, height, tile_rows):
        if should_cancel is not None and should_cancel():
            raise ProcessingCancelled("图像处理已取消。")
        bottom = min(height, top + tile_rows)
        output[top:bottom] = process_image(rgb[top:bottom], analysis, controls)
        if progress_callback is not None:
            progress_callback(bottom / max(1, height))
    if should_cancel is not None and should_cancel():
        raise ProcessingCancelled("图像处理已取消。")
    return output

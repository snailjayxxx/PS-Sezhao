from __future__ import annotations

import numpy as np

from .engine import Analysis, Controls, process_image, to_float_rgb


def process_image_tiled(
    image: np.ndarray,
    analysis: Analysis,
    controls: Controls | None = None,
    *,
    tile_rows: int = 384,
) -> np.ndarray:
    """Process a large scan in row tiles to cap temporary-array memory usage."""
    rgb = to_float_rgb(image)
    height = rgb.shape[0]
    tile_rows = max(32, int(tile_rows))
    output = np.empty(rgb.shape, dtype=np.float32)
    for top in range(0, height, tile_rows):
        bottom = min(height, top + tile_rows)
        output[top:bottom] = process_image(rgb[top:bottom], analysis, controls)
    return output

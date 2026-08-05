from __future__ import annotations

from typing import Iterable

from .workspace import FULL_CROP, clamp_crop, crop_to_pixels


def normalized_point(point: tuple[float, float], shape: tuple[int, ...]) -> tuple[float, float]:
    """Convert an image-space point to normalized coordinates."""
    height, width = int(shape[0]), int(shape[1])
    if height < 1 or width < 1:
        return 0.0, 0.0
    x = min(float(width), max(0.0, float(point[0]))) / float(width)
    y = min(float(height), max(0.0, float(point[1]))) / float(height)
    return x, y


def map_view_point_to_source(
    point: tuple[float, float],
    view_shape: tuple[int, ...],
    source_shape: tuple[int, ...],
    crop: Iterable[float] | None,
) -> tuple[float, float]:
    """Map a point from the visible cropped preview back to the original source.

    The visible image may contain only the applied crop, but eyedroppers must
    still sample the unmodified source image.  This function performs that
    coordinate conversion without using processed preview pixels.
    """
    view_height, view_width = int(view_shape[0]), int(view_shape[1])
    source_height, source_width = int(source_shape[0]), int(source_shape[1])
    if view_height < 1 or view_width < 1 or source_height < 1 or source_width < 1:
        return 0.0, 0.0
    x0, y0, x1, y1 = crop_to_pixels(source_shape, crop)
    local_x = min(float(view_width - 1), max(0.0, float(point[0])))
    local_y = min(float(view_height - 1), max(0.0, float(point[1])))
    span_x = max(1, x1 - x0)
    span_y = max(1, y1 - y0)
    source_x = x0 + local_x / max(1.0, float(view_width - 1)) * max(0, span_x - 1)
    source_y = y0 + local_y / max(1.0, float(view_height - 1)) * max(0, span_y - 1)
    return (
        min(float(source_width - 1), max(0.0, source_x)),
        min(float(source_height - 1), max(0.0, source_y)),
    )


def update_crop_from_drag(
    initial_crop: Iterable[float] | None,
    mode: str,
    start: tuple[float, float],
    current: tuple[float, float],
    *,
    min_size: float = 0.005,
) -> tuple[float, float, float, float]:
    """Resize, move or replace a normalized crop rectangle."""
    left, top, right, bottom = clamp_crop(initial_crop)
    sx, sy = (min(1.0, max(0.0, float(value))) for value in start)
    cx, cy = (min(1.0, max(0.0, float(value))) for value in current)
    minimum = min(0.25, max(0.0001, float(min_size)))

    if mode == "new":
        return _ordered_crop(sx, sy, cx, cy, minimum)

    if mode == "move":
        width = right - left
        height = bottom - top
        dx = cx - sx
        dy = cy - sy
        new_left = min(1.0 - width, max(0.0, left + dx))
        new_top = min(1.0 - height, max(0.0, top + dy))
        return clamp_crop((new_left, new_top, new_left + width, new_top + height))

    if "w" in mode:
        left = min(right - minimum, cx)
    if "e" in mode:
        right = max(left + minimum, cx)
    if "n" in mode:
        top = min(bottom - minimum, cy)
    if "s" in mode:
        bottom = max(top + minimum, cy)
    return clamp_crop((left, top, right, bottom))


def _ordered_crop(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    minimum: float,
) -> tuple[float, float, float, float]:
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    if right - left < minimum:
        right = min(1.0, left + minimum)
        left = max(0.0, right - minimum)
    if bottom - top < minimum:
        bottom = min(1.0, top + minimum)
        top = max(0.0, bottom - minimum)
    crop = clamp_crop((left, top, right, bottom))
    return crop if crop != FULL_CROP or minimum >= 1.0 else crop

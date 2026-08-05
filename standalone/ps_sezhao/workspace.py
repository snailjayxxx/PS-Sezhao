from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .core.geometry import GeometrySettings
from .raw_io import RAW_EXTENSIONS

SUPPORTED_EXTENSIONS = {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".webp"} | RAW_EXTENSIONS
FULL_CROP = (0.0, 0.0, 1.0, 1.0)
VALID_ROTATIONS = (0, 90, 180, 270)


def clamp_crop(crop: Iterable[float] | None) -> tuple[float, float, float, float]:
    if crop is None:
        return FULL_CROP
    values = list(crop)
    if len(values) != 4:
        return FULL_CROP
    left, top, right, bottom = (float(value) for value in values)
    left = min(1.0, max(0.0, left))
    top = min(1.0, max(0.0, top))
    right = min(1.0, max(0.0, right))
    bottom = min(1.0, max(0.0, bottom))
    if right < left:
        left, right = right, left
    if bottom < top:
        top, bottom = bottom, top
    if right - left < 1e-4 or bottom - top < 1e-4:
        return FULL_CROP
    return left, top, right, bottom


def normalize_rotation(value: int | float | str | None) -> int:
    try:
        degrees = int(round(float(value or 0) / 90.0)) * 90
    except (TypeError, ValueError):
        degrees = 0
    return degrees % 360


def rotate_array(image: np.ndarray, clockwise_degrees: int | float | str | None) -> np.ndarray:
    """Rotate an H×W×C image clockwise in 90-degree steps."""

    array = np.asarray(image)
    rotation = normalize_rotation(clockwise_degrees)
    if rotation == 0:
        return array.copy()
    turns_counter_clockwise = {90: -1, 180: 2, 270: 1}[rotation]
    return np.rot90(array, k=turns_counter_clockwise, axes=(0, 1)).copy()


def rotate_crop(
    crop: Iterable[float] | None,
    clockwise_degrees: int | float | str | None,
) -> tuple[float, float, float, float]:
    """Rotate a normalized crop rectangle with its source image."""

    left, top, right, bottom = clamp_crop(crop)
    rotation = normalize_rotation(clockwise_degrees)
    if rotation == 90:
        return clamp_crop((1.0 - bottom, left, 1.0 - top, right))
    if rotation == 180:
        return clamp_crop((1.0 - right, 1.0 - bottom, 1.0 - left, 1.0 - top))
    if rotation == 270:
        return clamp_crop((top, 1.0 - right, bottom, 1.0 - left))
    return left, top, right, bottom


def crop_to_pixels(
    shape: tuple[int, ...],
    crop: Iterable[float] | None,
) -> tuple[int, int, int, int]:
    if len(shape) < 2:
        raise ValueError("图像 shape 至少需要高度和宽度。")
    height, width = int(shape[0]), int(shape[1])
    if height < 1 or width < 1:
        raise ValueError("图像尺寸无效。")
    left, top, right, bottom = clamp_crop(crop)
    x0 = min(width - 1, max(0, int(round(left * width))))
    y0 = min(height - 1, max(0, int(round(top * height))))
    x1 = min(width, max(x0 + 1, int(round(right * width))))
    y1 = min(height, max(y0 + 1, int(round(bottom * height))))
    return x0, y0, x1, y1


def crop_array(image: np.ndarray, crop: Iterable[float] | None) -> np.ndarray:
    array = np.asarray(image)
    x0, y0, x1, y1 = crop_to_pixels(array.shape, crop)
    return array[y0:y1, x0:x1].copy()


def crop_is_full(crop: Iterable[float] | None, tolerance: float = 1e-6) -> bool:
    left, top, right, bottom = clamp_crop(crop)
    return (
        abs(left) <= tolerance
        and abs(top) <= tolerance
        and abs(right - 1.0) <= tolerance
        and abs(bottom - 1.0) <= tolerance
    )


def discover_images(folder: str | Path, *, recursive: bool = False) -> list[Path]:
    root = Path(folder)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"找不到图像文件夹：{root}")
    iterator = root.rglob("*") if recursive else root.glob("*")
    paths = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(paths, key=lambda path: (str(path.parent).lower(), path.name.lower()))


@dataclass
class PhotoState:
    path: Path
    controls: dict[str, object] = field(default_factory=dict)
    analysis: dict[str, object] | None = None
    crop: tuple[float, float, float, float] = FULL_CROP
    rotation: int = 0
    geometry: dict[str, Any] = field(default_factory=dict)
    raw_settings: dict[str, Any] = field(default_factory=dict)
    output_settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.crop = clamp_crop(self.crop)
        self.rotation = normalize_rotation(self.rotation)
        self.geometry = GeometrySettings.from_dict(self.geometry).to_dict()
        self.raw_settings = dict(self.raw_settings or {})
        self.output_settings = dict(self.output_settings or {})

    @property
    def crop_label(self) -> str:
        if crop_is_full(self.crop):
            label = "完整"
        else:
            left, top, right, bottom = self.crop
            width = max(0.0, right - left)
            height = max(0.0, bottom - top)
            label = f"{width * 100:.0f}% × {height * 100:.0f}%"
        geometry = GeometrySettings.from_dict(self.geometry)
        details: list[str] = []
        if self.rotation:
            details.append(f"{self.rotation}°")
        if abs(geometry.straighten) >= 0.05:
            details.append(f"拉直 {geometry.straighten:+.1f}°")
        if geometry.flip_horizontal:
            details.append("水平翻转")
        if geometry.flip_vertical:
            details.append("垂直翻转")
        return label if not details else f"{label} · {' · '.join(details)}"

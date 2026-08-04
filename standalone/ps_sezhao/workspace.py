from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np

SUPPORTED_EXTENSIONS = {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}
FULL_CROP = (0.0, 0.0, 1.0, 1.0)


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

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.crop = clamp_crop(self.crop)

    @property
    def crop_label(self) -> str:
        if crop_is_full(self.crop):
            return "完整"
        left, top, right, bottom = self.crop
        width = max(0.0, right - left)
        height = max(0.0, bottom - top)
        return f"{width * 100:.0f}% × {height * 100:.0f}%"

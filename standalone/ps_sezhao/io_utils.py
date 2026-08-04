from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageOps
import tifffile

TIFF_EXTENSIONS = {".tif", ".tiff"}
PIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_image(path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"找不到图像：{source}")
    suffix = source.suffix.lower()
    metadata: dict[str, Any] = {"path": str(source), "icc_profile": None, "source_dtype": None}

    if suffix in TIFF_EXTENSIONS:
        array = tifffile.imread(source)
        if array.ndim == 2:
            array = np.repeat(array[..., None], 3, axis=2)
        if array.ndim != 3:
            raise ValueError(f"暂不支持此 TIFF 结构：shape={array.shape}")
        if array.shape[2] > 3:
            array = array[..., :3]
        metadata["source_dtype"] = str(array.dtype)
        if np.issubdtype(array.dtype, np.integer):
            result = array.astype(np.float32) / float(np.iinfo(array.dtype).max)
        else:
            result = np.clip(array.astype(np.float32), 0.0, 1.0)
        return result, metadata

    if suffix not in PIL_EXTENSIONS:
        raise ValueError("当前独立版支持 TIFF、JPEG、PNG、BMP 和 WebP；RAW 请先导出为 16 位 TIFF。")

    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        metadata["icc_profile"] = image.info.get("icc_profile")
        rgb = image.convert("RGB")
        array = np.asarray(rgb, dtype=np.uint8)
    metadata["source_dtype"] = "uint8"
    return array.astype(np.float32) / 255.0, metadata


def save_image(
    path: str | Path,
    image: np.ndarray,
    *,
    bit_depth: int = 16,
    icc_profile: bytes | None = None,
    jpeg_quality: int = 95,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    suffix = destination.suffix.lower()

    if suffix in TIFF_EXTENSIONS:
        if bit_depth >= 16:
            data = np.round(rgb * 65535.0).astype(np.uint16)
        else:
            data = np.round(rgb * 255.0).astype(np.uint8)
        tifffile.imwrite(destination, data, photometric="rgb", metadata=None)
        return destination

    data8 = np.round(rgb * 255.0).astype(np.uint8)
    pil_image = Image.fromarray(data8, mode="RGB")
    kwargs: dict[str, Any] = {}
    if icc_profile:
        kwargs["icc_profile"] = icc_profile
    if suffix in {".jpg", ".jpeg"}:
        kwargs.update(quality=int(jpeg_quality), subsampling=0, optimize=True)
    elif suffix == ".png":
        kwargs.update(compress_level=4)
    pil_image.save(destination, **kwargs)
    return destination


def make_preview(image: np.ndarray, max_edge: int = 1800) -> np.ndarray:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    height, width, _ = rgb.shape
    if max(height, width) <= max_edge:
        return rgb.copy()
    scale = max_edge / float(max(height, width))
    target = (max(1, round(width * scale)), max(1, round(height * scale)))
    data8 = np.round(rgb * 255.0).astype(np.uint8)
    resized = Image.fromarray(data8, mode="RGB").resize(target, Image.Resampling.LANCZOS)
    return np.asarray(resized, dtype=np.float32) / 255.0

from __future__ import annotations

from io import BytesIO
from typing import Any, Mapping

import numpy as np
from PIL import Image, ImageCms

from ..color_profiles import PROPHOTO_RGB_V2_MICRO
from . import output as output_module


_PROPHOTO_TO_XYZ_D50 = np.asarray(
    (
        (0.7976749, 0.1351917, 0.0313534),
        (0.2880402, 0.7118741, 0.0000857),
        (0.0, 0.0, 0.8252100),
    ),
    dtype=np.float64,
)
_XYZ_D50_TO_PROPHOTO = np.linalg.inv(_PROPHOTO_TO_XYZ_D50)
_D50_TO_D65 = np.asarray(
    (
        (0.9555766, -0.0230393, 0.0631636),
        (-0.0282895, 1.0099416, 0.0210077),
        (0.0122982, -0.0204830, 1.3299098),
    ),
    dtype=np.float64,
)
_D65_TO_D50 = np.linalg.inv(_D50_TO_D65)
_XYZ_D65_TO_SRGB = np.asarray(
    (
        (3.2404542, -1.5371385, -0.4985314),
        (-0.9692660, 1.8760108, 0.0415560),
        (0.0556434, -0.2040259, 1.0572252),
    ),
    dtype=np.float64,
)
_SRGB_TO_XYZ_D65 = np.linalg.inv(_XYZ_D65_TO_SRGB)


def install_output_color_conversion() -> None:
    if getattr(output_module, "_bidirectional_color_conversion_applied", False):
        return
    output_module.convert_color_space = convert_color_space
    output_module._prophoto_to_srgb = prophoto_to_srgb
    output_module._srgb_to_prophoto = srgb_to_prophoto
    output_module._bidirectional_color_conversion_applied = True


def convert_color_space(
    image: np.ndarray,
    color_space: str,
    *,
    source_icc_profile: bytes | None,
    source_metadata: Mapping[str, Any] | None = None,
) -> tuple[np.ndarray, bytes | None]:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    target = color_space if color_space in output_module.COLOR_SPACES else "preserve"
    if target == "preserve":
        return rgb.copy(), source_icc_profile

    source_kind = _source_space(source_icc_profile, source_metadata)
    if target == "srgb":
        if source_kind == "prophoto":
            return prophoto_to_srgb(rgb), output_module.SRGB_ICC_PROFILE or None
        if source_kind == "srgb":
            return rgb.copy(), output_module.SRGB_ICC_PROFILE or source_icc_profile
        converted = _lcms_convert(
            rgb,
            source_icc_profile,
            output_module.SRGB_ICC_PROFILE,
        )
        return converted, output_module.SRGB_ICC_PROFILE or None

    if source_kind == "prophoto":
        return rgb.copy(), PROPHOTO_RGB_V2_MICRO
    if source_kind == "srgb":
        return srgb_to_prophoto(rgb), PROPHOTO_RGB_V2_MICRO
    converted = _lcms_convert(
        rgb,
        source_icc_profile,
        PROPHOTO_RGB_V2_MICRO,
    )
    return converted, PROPHOTO_RGB_V2_MICRO


def prophoto_to_srgb(image: np.ndarray) -> np.ndarray:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    output = np.empty_like(rgb, dtype=np.float32)
    transform = _XYZ_D65_TO_SRGB @ _D50_TO_D65 @ _PROPHOTO_TO_XYZ_D50
    for top in range(0, rgb.shape[0], 512):
        block = rgb[top : top + 512]
        linear = np.power(block.astype(np.float64), 1.8)
        converted = linear.reshape(-1, 3) @ transform.T
        converted = np.clip(converted, 0.0, 1.0)
        encoded = np.where(
            converted <= 0.0031308,
            converted * 12.92,
            1.055 * np.power(converted, 1.0 / 2.4) - 0.055,
        )
        output[top : top + block.shape[0]] = encoded.reshape(block.shape).astype(np.float32)
    return np.clip(output, 0.0, 1.0)


def srgb_to_prophoto(image: np.ndarray) -> np.ndarray:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    output = np.empty_like(rgb, dtype=np.float32)
    transform = _XYZ_D50_TO_PROPHOTO @ _D65_TO_D50 @ _SRGB_TO_XYZ_D65
    for top in range(0, rgb.shape[0], 512):
        block = rgb[top : top + 512].astype(np.float64)
        linear = np.where(
            block <= 0.04045,
            block / 12.92,
            np.power((block + 0.055) / 1.055, 2.4),
        )
        converted = linear.reshape(-1, 3) @ transform.T
        converted = np.clip(converted, 0.0, 1.0)
        encoded = np.power(converted, 1.0 / 1.8)
        output[top : top + block.shape[0]] = encoded.reshape(block.shape).astype(np.float32)
    return np.clip(output, 0.0, 1.0)


def _source_space(
    profile: bytes | None,
    metadata: Mapping[str, Any] | None,
) -> str:
    if metadata and metadata.get("linear_raw"):
        return "prophoto"
    if profile == PROPHOTO_RGB_V2_MICRO:
        return "prophoto"
    if not profile:
        return "srgb"
    if output_module.SRGB_ICC_PROFILE and profile == output_module.SRGB_ICC_PROFILE:
        return "srgb"
    try:
        parsed = ImageCms.ImageCmsProfile(BytesIO(profile))
        description = ImageCms.getProfileDescription(parsed).lower()
        if "prophoto" in description or "romm" in description:
            return "prophoto"
        if "srgb" in description:
            return "srgb"
    except Exception:
        pass
    return "other"


def _lcms_convert(
    image: np.ndarray,
    source_profile: bytes | None,
    target_profile: bytes | None,
) -> np.ndarray:
    if not source_profile or not target_profile:
        return np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0).copy()
    try:
        source = ImageCms.ImageCmsProfile(BytesIO(source_profile))
        target = ImageCms.ImageCmsProfile(BytesIO(target_profile))
        data8 = np.round(np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
        converted = ImageCms.profileToProfile(
            Image.fromarray(data8, mode="RGB"),
            source,
            target,
            outputMode="RGB",
            renderingIntent=ImageCms.Intent.PERCEPTUAL,
        )
        return np.asarray(converted, dtype=np.uint8).astype(np.float32) / 255.0
    except Exception as error:
        raise ValueError(f"无法转换输入 ICC 色彩空间：{error}") from error


install_output_color_conversion()

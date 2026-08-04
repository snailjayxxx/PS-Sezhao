from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import math

import numpy as np

EPSILON = 1.0 / 65535.0

PROFILES: dict[str, dict[str, Any]] = {
    "generic": {
        "label": "通用 C-41",
        "gamma": (1.0, 1.0, 1.0),
        "matrix": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "saturation": 1.0,
        "contrast": 1.0,
        "temperature": 0.0,
        "tint": 0.0,
    },
    "portra": {
        "label": "Kodak Portra 起始风格",
        "gamma": (1.03, 1.0, 0.98),
        "matrix": ((1.025, -0.010, -0.015), (-0.010, 1.020, -0.010), (-0.010, -0.015, 1.025)),
        "saturation": 0.94,
        "contrast": 0.96,
        "temperature": 0.10,
        "tint": 0.02,
    },
    "gold": {
        "label": "Kodak Gold 起始风格",
        "gamma": (1.05, 1.0, 0.96),
        "matrix": ((1.055, -0.020, -0.035), (-0.005, 1.015, -0.010), (-0.020, -0.010, 1.030)),
        "saturation": 1.08,
        "contrast": 1.05,
        "temperature": 0.18,
        "tint": 0.01,
    },
    "fuji": {
        "label": "Fujifilm C-41 起始风格",
        "gamma": (0.99, 1.02, 1.01),
        "matrix": ((1.015, -0.010, -0.005), (-0.015, 1.045, -0.030), (-0.010, -0.020, 1.030)),
        "saturation": 1.04,
        "contrast": 1.0,
        "temperature": -0.04,
        "tint": -0.02,
    },
    "ecn2": {
        "label": "ECN-2 低反差起始风格",
        "gamma": (1.0, 1.0, 1.0),
        "matrix": ((1.020, -0.010, -0.010), (-0.010, 1.025, -0.015), (-0.010, -0.010, 1.020)),
        "saturation": 0.92,
        "contrast": 0.88,
        "temperature": 0.02,
        "tint": 0.0,
    },
}


@dataclass
class Analysis:
    base: tuple[float, float, float]
    black: tuple[float, float, float]
    white: tuple[float, float, float]
    confidence: float = 1.0
    method: str = "manual"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Analysis":
        return cls(
            base=tuple(float(v) for v in value["base"]),
            black=tuple(float(v) for v in value["black"]),
            white=tuple(float(v) for v in value["white"]),
            confidence=float(value.get("confidence", 1.0)),
            method=str(value.get("method", "saved")),
        )


@dataclass
class Controls:
    profile: str = "generic"
    style_strength: float = 1.0
    exposure: float = 0.0
    contrast: float = 1.0
    gamma: float = 1.0
    saturation: float = 1.0
    temperature: float = 0.0
    tint: float = 0.0
    red_gain: float = 1.0
    green_gain: float = 1.0
    blue_gain: float = 1.0
    black_point: float = 0.0
    white_point: float = 0.0
    shadows: float = 0.0
    highlights: float = 0.0
    base_adjust: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def sanitized(self) -> "Controls":
        return Controls(
            profile=self.profile if self.profile in PROFILES else "generic",
            style_strength=float(np.clip(self.style_strength, 0.0, 2.5)),
            exposure=float(np.clip(self.exposure, -6.0, 6.0)),
            contrast=float(np.clip(self.contrast, 0.1, 4.0)),
            gamma=float(np.clip(self.gamma, 0.1, 4.0)),
            saturation=float(np.clip(self.saturation, 0.0, 5.0)),
            temperature=float(np.clip(self.temperature, -3.0, 3.0)),
            tint=float(np.clip(self.tint, -2.5, 2.5)),
            red_gain=float(np.clip(self.red_gain, 0.1, 4.0)),
            green_gain=float(np.clip(self.green_gain, 0.1, 4.0)),
            blue_gain=float(np.clip(self.blue_gain, 0.1, 4.0)),
            black_point=float(np.clip(self.black_point, -1.0, 1.0)),
            white_point=float(np.clip(self.white_point, -1.0, 1.0)),
            shadows=float(np.clip(self.shadows, -1.0, 1.0)),
            highlights=float(np.clip(self.highlights, -1.0, 1.0)),
            base_adjust=tuple(float(np.clip(v, -0.35, 0.35)) for v in self.base_adjust),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "Controls":
        if not value:
            return cls()
        aliases = {
            "styleStrength": "style_strength",
            "redGain": "red_gain",
            "greenGain": "green_gain",
            "blueGain": "blue_gain",
            "blackPoint": "black_point",
            "whitePoint": "white_point",
            "baseAdjust": "base_adjust",
        }
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized[aliases.get(key, key)] = item
        if "base_adjust" in normalized:
            normalized["base_adjust"] = tuple(float(v) for v in normalized["base_adjust"])
        allowed = set(cls.__dataclass_fields__.keys())
        return cls(**{key: val for key, val in normalized.items() if key in allowed}).sanitized()


def _ensure_rgb(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim == 2:
        array = np.repeat(array[..., None], 3, axis=2)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("图像必须包含至少三个颜色通道。")
    return array[..., :3]


def to_float_rgb(image: np.ndarray) -> np.ndarray:
    rgb = _ensure_rgb(image)
    if np.issubdtype(rgb.dtype, np.integer):
        max_value = float(np.iinfo(rgb.dtype).max)
        return rgb.astype(np.float32) / max_value
    return np.clip(rgb.astype(np.float32), 0.0, 1.0)


def estimate_base_from_border(image: np.ndarray, border_fraction: float = 0.07) -> tuple[np.ndarray, float]:
    rgb = to_float_rgb(image)
    height, width, _ = rgb.shape
    border_fraction = float(np.clip(border_fraction, 0.02, 0.25))
    border_x = max(2, round(width * border_fraction))
    border_y = max(2, round(height * border_fraction))
    mask = np.zeros((height, width), dtype=bool)
    mask[:border_y, :] = True
    mask[-border_y:, :] = True
    mask[:, :border_x] = True
    mask[:, -border_x:] = True
    pixels = rgb[mask]
    if pixels.shape[0] > 150_000:
        step = max(1, pixels.shape[0] // 150_000)
        pixels = pixels[::step]
    luma = pixels @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    valid = (luma > 0.10) & (luma < 0.998)
    pixels = pixels[valid]
    if pixels.shape[0] < 24:
        raise ValueError("边框中没有足够的有效胶片基底像素，请改用吸管取样。")
    score = (pixels[:, 0] - pixels[:, 2]) + 0.30 * (pixels[:, 0] - pixels[:, 1])
    threshold = np.quantile(score, 0.45)
    selected = pixels[score >= threshold]
    if selected.shape[0] < 24:
        selected = pixels
    base = np.median(selected, axis=0)
    deviations = np.mean(np.abs(selected - base), axis=1)
    mad = float(np.median(deviations))
    orange_score = float(np.clip((base[0] - base[2]) * 1.8 + (base[0] - base[1]) * 0.5, 0.0, 1.0))
    consistency = float(np.clip(1.0 - mad * 8.0, 0.0, 1.0))
    coverage = float(np.clip(selected.shape[0] / 500.0, 0.0, 1.0))
    confidence = float(np.clip(0.15 + orange_score * 0.40 + consistency * 0.35 + coverage * 0.10, 0.0, 1.0))
    return base.astype(np.float32), confidence


def sample_patch(image: np.ndarray, x: int, y: int, size: int = 11) -> np.ndarray:
    rgb = to_float_rgb(image)
    height, width, _ = rgb.shape
    radius = max(0, int(size) // 2)
    left = max(0, int(x) - radius)
    right = min(width, int(x) + radius + 1)
    top = max(0, int(y) - radius)
    bottom = min(height, int(y) + radius + 1)
    patch = rgb[top:bottom, left:right]
    if patch.size == 0:
        raise ValueError("取样点不在图像范围内。")
    return patch


def sample_median_rgb(image: np.ndarray, x: int, y: int, size: int = 11) -> np.ndarray:
    patch = sample_patch(image, x, y, size)
    return np.median(patch.reshape(-1, 3), axis=0).astype(np.float32)


def analyze_tone_range(image: np.ndarray, base: np.ndarray, border_fraction: float = 0.07) -> tuple[np.ndarray, np.ndarray]:
    rgb = to_float_rgb(image)
    height, width, _ = rgb.shape
    margin_x = int(width * float(np.clip(border_fraction, 0.0, 0.25)))
    margin_y = int(height * float(np.clip(border_fraction, 0.0, 0.25)))
    inner = rgb[margin_y:max(margin_y + 1, height - margin_y), margin_x:max(margin_x + 1, width - margin_x)]
    flat = inner.reshape(-1, 3)
    if flat.shape[0] > 250_000:
        step = max(1, flat.shape[0] // 250_000)
        flat = flat[::step]
    density = np.maximum(0.0, np.log(np.maximum(base, EPSILON) / np.maximum(flat, EPSILON)))
    if density.shape[0] < 32:
        raise ValueError("画面有效像素不足，无法计算转正范围。")
    black = np.quantile(density, 0.01, axis=0)
    white = np.quantile(density, 0.995, axis=0)
    white = np.maximum(white, black + 0.02)
    return black.astype(np.float32), white.astype(np.float32)


def analyze_image(image: np.ndarray, border_fraction: float = 0.07, base: np.ndarray | None = None, method: str = "border") -> Analysis:
    if base is None:
        base, confidence = estimate_base_from_border(image, border_fraction)
    else:
        base = np.asarray(base, dtype=np.float32)
        confidence = 1.0
    black, white = analyze_tone_range(image, base, border_fraction)
    return Analysis(tuple(float(v) for v in base), tuple(float(v) for v in black), tuple(float(v) for v in white), confidence, method)


def _blend_matrix(matrix: np.ndarray, amount: float) -> np.ndarray:
    return np.eye(3, dtype=np.float32) + (matrix - np.eye(3, dtype=np.float32)) * amount


def process_image(image: np.ndarray, analysis: Analysis, controls: Controls | None = None) -> np.ndarray:
    controls = (controls or Controls()).sanitized()
    rgb = to_float_rgb(image)
    profile = PROFILES[controls.profile]
    base = np.clip(np.asarray(analysis.base, dtype=np.float32) + np.asarray(controls.base_adjust, dtype=np.float32), EPSILON, 1.5)
    black = np.asarray(analysis.black, dtype=np.float32)
    white = np.asarray(analysis.white, dtype=np.float32)

    density = np.maximum(0.0, np.log(np.maximum(base, EPSILON) / np.maximum(rgb, EPSILON)))
    normalized = np.clip((density - black) / np.maximum(white - black, 0.0001), 0.0, 1.0)
    profile_gamma = 1.0 + (np.asarray(profile["gamma"], dtype=np.float32) - 1.0) * controls.style_strength
    normalized = np.power(normalized, 1.0 / np.maximum(profile_gamma, 0.1))

    matrix = _blend_matrix(np.asarray(profile["matrix"], dtype=np.float32), controls.style_strength)
    out = normalized @ matrix.T
    combined_contrast = (1.0 + (float(profile["contrast"]) - 1.0) * controls.style_strength) * controls.contrast
    combined_saturation = (1.0 + (float(profile["saturation"]) - 1.0) * controls.style_strength) * controls.saturation
    combined_temperature = float(profile["temperature"]) * controls.style_strength + controls.temperature
    combined_tint = float(profile["tint"]) * controls.style_strength + controls.tint

    out = (out - 0.5) * combined_contrast + 0.5
    black_shift = controls.black_point * 0.18
    white_shift = controls.white_point * 0.18
    denominator = max(0.10, 1.0 + white_shift - black_shift)
    out = (out - black_shift) / denominator
    clipped = np.clip(out, 0.0, 1.0)
    out = out + controls.shadows * np.square(1.0 - clipped) * 0.28
    out = out + controls.highlights * np.square(clipped) * 0.28
    out = np.clip(out * math.pow(2.0, controls.exposure), 0.0, 1.0)
    out = np.power(out, 1.0 / controls.gamma)

    luma = out[..., 0] * 0.2126 + out[..., 1] * 0.7152 + out[..., 2] * 0.0722
    out = luma[..., None] + (out - luma[..., None]) * combined_saturation

    red_scale = math.exp(0.30 * combined_temperature + 0.10 * combined_tint)
    green_scale = math.exp(0.03 * combined_temperature - 0.22 * combined_tint)
    blue_scale = math.exp(-0.34 * combined_temperature + 0.10 * combined_tint)
    out *= np.asarray(
        [red_scale * controls.red_gain, green_scale * controls.green_gain, blue_scale * controls.blue_gain],
        dtype=np.float32,
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def neutral_gains(
    image: np.ndarray,
    analysis: Analysis,
    controls: Controls,
    x: int,
    y: int,
    size: int = 11,
) -> tuple[float, float, float]:
    patch = sample_patch(image, x, y, size)
    processed = process_image(patch, analysis, controls)
    average = np.median(processed.reshape(-1, 3), axis=0)
    target = float(np.clip(average @ np.array([0.2126, 0.7152, 0.0722]), 0.05, 0.95))
    current = controls.sanitized()
    gains = np.array([current.red_gain, current.green_gain, current.blue_gain], dtype=np.float32)
    gains *= target / np.maximum(average, 0.01)
    gains = np.clip(gains, 0.25, 3.0)
    return tuple(float(v) for v in gains)

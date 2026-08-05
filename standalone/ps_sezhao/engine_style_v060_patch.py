from __future__ import annotations

from dataclasses import asdict
import math
from typing import Any, Mapping

import numpy as np

from . import engine
from . import processing

IDENTITY_MATRIX = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)

SCANNER_PROFILE_ORDER = (
    "neutral_lab",
    "hasselblad_flextight_x5",
    "noritsu_hs1800",
    "frontier_sp3000_soft",
    "frontier_sp3000_vivid",
    "archive_flatbed",
)

SCANNER_PROFILES: dict[str, dict[str, Any]] = {
    "neutral_lab": {
        "label": "中性实验室 · 干净扫描",
        "description": "中性反差和色彩，适合先完成准确转正后再手动调色。",
        "gamma": (1.0, 1.0, 1.0),
        "matrix": IDENTITY_MATRIX,
        "saturation": 1.0,
        "contrast": 1.0,
        "temperature": 0.0,
        "tint": 0.0,
    },
    "hasselblad_flextight_x5": {
        "label": "Hasselblad Flextight X5 · 高端扫描风格参考",
        "description": "偏中性、细腻、微反差清楚，高光保持克制。",
        "gamma": (1.010, 1.000, 0.995),
        "matrix": ((1.012, -0.006, -0.006), (-0.004, 1.010, -0.006), (-0.004, -0.006, 1.010)),
        "saturation": 0.98,
        "contrast": 1.03,
        "temperature": 0.01,
        "tint": 0.005,
    },
    "noritsu_hs1800": {
        "label": "Noritsu HS-1800 · 日系冲扫风格参考",
        "description": "肤色略暖、层次柔顺，适合人像和日常照片。",
        "gamma": (1.015, 1.000, 0.985),
        "matrix": ((1.028, -0.012, -0.016), (-0.008, 1.018, -0.010), (-0.010, -0.012, 1.022)),
        "saturation": 1.04,
        "contrast": 1.02,
        "temperature": 0.05,
        "tint": 0.015,
    },
    "frontier_sp3000_soft": {
        "label": "Fujifilm Frontier SP-3000 · 柔和风格参考",
        "description": "反差柔和、青绿清爽，适合清淡日系观感。",
        "gamma": (0.995, 1.010, 1.015),
        "matrix": ((1.010, -0.008, -0.002), (-0.012, 1.030, -0.018), (-0.006, -0.014, 1.020)),
        "saturation": 1.02,
        "contrast": 0.96,
        "temperature": -0.025,
        "tint": -0.015,
    },
    "frontier_sp3000_vivid": {
        "label": "Fujifilm Frontier SP-3000 · 浓郁风格参考",
        "description": "更鲜明的色彩和反差，适合街拍、旅行和阳光场景。",
        "gamma": (1.010, 1.000, 1.000),
        "matrix": ((1.030, -0.018, -0.012), (-0.016, 1.050, -0.034), (-0.010, -0.020, 1.030)),
        "saturation": 1.10,
        "contrast": 1.08,
        "temperature": 0.0,
        "tint": -0.01,
    },
    "archive_flatbed": {
        "label": "Archive Flatbed · 档案平板扫描",
        "description": "低反差、低饱和、保留宽容度，适合作为后期档案底稿。",
        "gamma": (1.0, 1.0, 1.0),
        "matrix": IDENTITY_MATRIX,
        "saturation": 0.96,
        "contrast": 0.92,
        "temperature": 0.0,
        "tint": 0.0,
    },
}

FILM_PROFILE_ORDER = (
    "generic",
    "kodak_portra_160",
    "kodak_portra_400",
    "kodak_portra_800",
    "kodak_gold_200",
    "kodak_ektar_100",
    "kodak_ultramax_400",
    "fujifilm_pro_400h",
    "fujifilm_superia_400",
    "fujifilm_c200",
    "cinestill_50d",
    "cinestill_800t",
    "kodak_vision3_250d",
    "kodak_vision3_500t",
    "ilford_hp5_plus_400",
    "kodak_trix_400",
)

FILM_PROFILES: dict[str, dict[str, Any]] = {
    "generic": {
        "label": "无胶卷风格 · 中性转正",
        "description": "不附加胶卷色彩，只执行基础去色罩和转正。",
        "gamma": (1.0, 1.0, 1.0),
        "matrix": IDENTITY_MATRIX,
        "saturation": 1.0,
        "contrast": 1.0,
        "temperature": 0.0,
        "tint": 0.0,
    },
    "kodak_portra_160": {
        "label": "Kodak Portra 160 · 细腻低饱和",
        "description": "柔和反差、细腻肤色和较低饱和度。",
        "gamma": (1.020, 1.000, 0.985),
        "matrix": ((1.018, -0.006, -0.012), (-0.008, 1.016, -0.008), (-0.006, -0.012, 1.018)),
        "saturation": 0.88,
        "contrast": 0.94,
        "temperature": 0.06,
        "tint": 0.02,
    },
    "kodak_portra_400": {
        "label": "Kodak Portra 400 · 柔和人像",
        "description": "暖润肤色、柔和高光和均衡的日常人像观感。",
        "gamma": (1.030, 1.000, 0.980),
        "matrix": ((1.025, -0.010, -0.015), (-0.010, 1.020, -0.010), (-0.010, -0.015, 1.025)),
        "saturation": 0.94,
        "contrast": 0.96,
        "temperature": 0.10,
        "tint": 0.025,
    },
    "kodak_portra_800": {
        "label": "Kodak Portra 800 · 暖调高感",
        "description": "更暖、更浓的肤色与夜景氛围，保留柔和反差。",
        "gamma": (1.040, 1.000, 0.970),
        "matrix": ((1.035, -0.012, -0.023), (-0.010, 1.022, -0.012), (-0.014, -0.016, 1.030)),
        "saturation": 0.98,
        "contrast": 0.98,
        "temperature": 0.15,
        "tint": 0.03,
    },
    "kodak_gold_200": {
        "label": "Kodak Gold 200 · 暖色复古",
        "description": "金黄色调、较高饱和和鲜明的家庭照片观感。",
        "gamma": (1.050, 1.000, 0.960),
        "matrix": ((1.055, -0.020, -0.035), (-0.005, 1.015, -0.010), (-0.020, -0.010, 1.030)),
        "saturation": 1.10,
        "contrast": 1.06,
        "temperature": 0.18,
        "tint": 0.01,
    },
    "kodak_ektar_100": {
        "label": "Kodak Ektar 100 · 高饱和风光",
        "description": "红蓝更鲜明、反差较强，适合风光、建筑和产品。",
        "gamma": (1.020, 1.000, 0.990),
        "matrix": ((1.075, -0.030, -0.045), (-0.015, 1.035, -0.020), (-0.025, -0.020, 1.045)),
        "saturation": 1.18,
        "contrast": 1.10,
        "temperature": 0.03,
        "tint": 0.01,
    },
    "kodak_ultramax_400": {
        "label": "Kodak Ultramax 400 · 通用日常",
        "description": "暖调、明快、较强饱和，适合旅行和日常快照。",
        "gamma": (1.035, 1.000, 0.975),
        "matrix": ((1.050, -0.018, -0.032), (-0.010, 1.025, -0.015), (-0.016, -0.014, 1.030)),
        "saturation": 1.12,
        "contrast": 1.07,
        "temperature": 0.10,
        "tint": 0.005,
    },
    "fujifilm_pro_400h": {
        "label": "Fujifilm Pro 400H · 清淡粉绿",
        "description": "低饱和、柔和反差和清淡粉绿的人像观感。",
        "gamma": (0.995, 1.015, 1.010),
        "matrix": ((1.010, -0.006, -0.004), (-0.012, 1.035, -0.023), (-0.004, -0.015, 1.019)),
        "saturation": 0.92,
        "contrast": 0.94,
        "temperature": -0.02,
        "tint": 0.02,
    },
    "fujifilm_superia_400": {
        "label": "Fujifilm Superia X-TRA 400 · 清爽日常",
        "description": "青绿更明显，饱和和反差适中，适合街拍和生活记录。",
        "gamma": (0.990, 1.020, 1.010),
        "matrix": ((1.015, -0.010, -0.005), (-0.015, 1.045, -0.030), (-0.010, -0.020, 1.030)),
        "saturation": 1.06,
        "contrast": 1.02,
        "temperature": -0.04,
        "tint": -0.015,
    },
    "fujifilm_c200": {
        "label": "Fujifilm C200 · 轻复古日常",
        "description": "稍柔的反差、清爽蓝绿和轻微暖色复古感。",
        "gamma": (1.000, 1.015, 1.005),
        "matrix": ((1.018, -0.010, -0.008), (-0.012, 1.038, -0.026), (-0.008, -0.018, 1.026)),
        "saturation": 1.03,
        "contrast": 0.98,
        "temperature": 0.02,
        "tint": -0.01,
    },
    "cinestill_50d": {
        "label": "CineStill 50D · 日光电影感",
        "description": "日光平衡、细腻、低至中等反差的电影感色彩。",
        "gamma": (1.010, 1.000, 0.990),
        "matrix": ((1.030, -0.012, -0.018), (-0.010, 1.025, -0.015), (-0.010, -0.018, 1.028)),
        "saturation": 1.05,
        "contrast": 0.98,
        "temperature": 0.03,
        "tint": 0.01,
    },
    "cinestill_800t": {
        "label": "CineStill 800T · 钨丝霓虹",
        "description": "明显冷调和蓝色夜景倾向，适合霓虹与城市夜拍。",
        "gamma": (0.980, 1.000, 1.030),
        "matrix": ((1.020, -0.010, -0.010), (-0.015, 1.025, -0.010), (-0.020, -0.020, 1.040)),
        "saturation": 1.08,
        "contrast": 1.02,
        "temperature": -0.22,
        "tint": 0.03,
    },
    "kodak_vision3_250d": {
        "label": "Kodak Vision3 250D · 电影日光",
        "description": "低反差、柔和高光和自然日光电影色彩。",
        "gamma": (1.000, 1.000, 1.000),
        "matrix": ((1.020, -0.010, -0.010), (-0.010, 1.025, -0.015), (-0.010, -0.010, 1.020)),
        "saturation": 0.92,
        "contrast": 0.88,
        "temperature": 0.04,
        "tint": 0.01,
    },
    "kodak_vision3_500t": {
        "label": "Kodak Vision3 500T · 电影夜景",
        "description": "更低反差、冷调阴影和柔和的钨丝夜景观感。",
        "gamma": (0.990, 1.000, 1.020),
        "matrix": ((1.015, -0.008, -0.007), (-0.010, 1.020, -0.010), (-0.015, -0.012, 1.027)),
        "saturation": 0.90,
        "contrast": 0.86,
        "temperature": -0.12,
        "tint": 0.02,
    },
    "ilford_hp5_plus_400": {
        "label": "Ilford HP5 Plus 400 · 经典黑白",
        "description": "柔和到中等反差的经典黑白，适合人像和纪实。",
        "gamma": (1.030, 1.030, 1.030),
        "matrix": IDENTITY_MATRIX,
        "saturation": 0.0,
        "contrast": 1.10,
        "temperature": 0.0,
        "tint": 0.0,
        "monochrome": True,
    },
    "kodak_trix_400": {
        "label": "Kodak Tri-X 400 · 纪实黑白",
        "description": "更强反差和更有力量的纪实黑白观感。",
        "gamma": (1.060, 1.060, 1.060),
        "matrix": IDENTITY_MATRIX,
        "saturation": 0.0,
        "contrast": 1.18,
        "temperature": 0.0,
        "tint": 0.0,
        "monochrome": True,
    },
}

FILM_PROFILE_ALIASES = {
    "portra": "kodak_portra_400",
    "gold": "kodak_gold_200",
    "fuji": "fujifilm_superia_400",
    "ecn2": "kodak_vision3_250d",
}


def canonical_film_profile(value: Any) -> str:
    name = str(value or "generic")
    name = FILM_PROFILE_ALIASES.get(name, name)
    return name if name in FILM_PROFILES else "generic"


def canonical_scanner_profile(value: Any) -> str:
    name = str(value or "neutral_lab")
    return name if name in SCANNER_PROFILES else "neutral_lab"


def _blend_matrix(matrix: np.ndarray, amount: float) -> np.ndarray:
    identity = np.eye(3, dtype=np.float32)
    return identity + (matrix - identity) * float(amount)


def _style_gamma(image: np.ndarray, gamma: Any, strength: float) -> np.ndarray:
    value = 1.0 + (np.asarray(gamma, dtype=np.float32) - 1.0) * float(strength)
    return np.power(np.clip(image, 0.0, 1.0), 1.0 / np.maximum(value, 0.1))


def _style_matrix(image: np.ndarray, matrix: Any, strength: float) -> np.ndarray:
    blended = _blend_matrix(np.asarray(matrix, dtype=np.float32), strength)
    return image @ blended.T


def _process_image_v060(
    image: np.ndarray,
    analysis: engine.Analysis,
    controls: engine.Controls | None = None,
) -> np.ndarray:
    controls = (controls or engine.Controls()).sanitized()
    rgb = engine.to_float_rgb(image)
    film = FILM_PROFILES[canonical_film_profile(controls.profile)]
    scanner_name = canonical_scanner_profile(getattr(controls, "scanner_profile", "neutral_lab"))
    scanner = SCANNER_PROFILES[scanner_name]
    film_strength = float(controls.style_strength)
    scanner_strength = float(getattr(controls, "scanner_strength", 1.0))

    base = np.clip(
        np.asarray(analysis.base, dtype=np.float32) + np.asarray(controls.base_adjust, dtype=np.float32),
        engine.EPSILON,
        1.5,
    )
    black = np.asarray(analysis.black, dtype=np.float32)
    white = np.asarray(analysis.white, dtype=np.float32)
    density = np.maximum(0.0, np.log(np.maximum(base, engine.EPSILON) / np.maximum(rgb, engine.EPSILON)))
    out = np.clip((density - black) / np.maximum(white - black, 0.0001), 0.0, 1.0)

    out = _style_gamma(out, scanner["gamma"], scanner_strength)
    out = _style_matrix(out, scanner["matrix"], scanner_strength)
    out = _style_gamma(out, film["gamma"], film_strength)
    out = _style_matrix(out, film["matrix"], film_strength)

    combined_contrast = (
        (1.0 + (float(scanner["contrast"]) - 1.0) * scanner_strength)
        * (1.0 + (float(film["contrast"]) - 1.0) * film_strength)
        * controls.contrast
    )
    combined_saturation = (
        (1.0 + (float(scanner["saturation"]) - 1.0) * scanner_strength)
        * (1.0 + (float(film["saturation"]) - 1.0) * film_strength)
        * controls.saturation
    )
    style_temperature = (
        float(scanner["temperature"]) * scanner_strength
        + float(film["temperature"]) * film_strength
    )
    style_tint = float(scanner["tint"]) * scanner_strength + float(film["tint"]) * film_strength
    if film.get("monochrome"):
        style_temperature = 0.0
        style_tint = 0.0
    combined_temperature = style_temperature + controls.temperature
    combined_tint = style_tint + controls.tint

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
        [
            red_scale * controls.red_gain,
            green_scale * controls.green_gain,
            blue_scale * controls.blue_gain,
        ],
        dtype=np.float32,
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _neutral_gains_v060(
    image: np.ndarray,
    analysis: engine.Analysis,
    controls: engine.Controls,
    x: int,
    y: int,
    size: int = 11,
) -> tuple[float, float, float]:
    patch = engine.sample_patch(image, x, y, size)
    processed = _process_image_v060(patch, analysis, controls)
    average = np.median(processed.reshape(-1, 3), axis=0)
    target = float(np.clip(average @ np.array([0.2126, 0.7152, 0.0722]), 0.05, 0.95))
    current = controls.sanitized()
    gains = np.asarray([current.red_gain, current.green_gain, current.blue_gain], dtype=np.float32)
    gains *= target / np.maximum(average, 0.01)
    gains = np.clip(gains, 0.25, 3.0)
    return tuple(float(value) for value in gains)


def apply_style_engine_patch() -> None:
    controls_class = engine.Controls
    if getattr(controls_class, "_v060_style_library_applied", False):
        return

    original_sanitized = controls_class.sanitized
    original_from_dict = controls_class.from_dict

    def sanitized(self: engine.Controls) -> engine.Controls:
        result = original_sanitized(self)
        result.profile = canonical_film_profile(result.profile)
        result.scanner_profile = canonical_scanner_profile(
            getattr(self, "scanner_profile", "neutral_lab")
        )
        result.scanner_strength = float(
            np.clip(getattr(self, "scanner_strength", 1.0), 0.0, 2.5)
        )
        return result

    def to_dict(self: engine.Controls) -> dict[str, Any]:
        payload = asdict(self)
        payload["profile"] = canonical_film_profile(payload.get("profile"))
        payload["scanner_profile"] = canonical_scanner_profile(
            getattr(self, "scanner_profile", "neutral_lab")
        )
        payload["scanner_strength"] = float(
            np.clip(getattr(self, "scanner_strength", 1.0), 0.0, 2.5)
        )
        return payload

    @classmethod
    def from_dict(cls: type[engine.Controls], value: Mapping[str, Any] | None) -> engine.Controls:
        normalized = dict(value or {})
        if "scannerProfile" in normalized and "scanner_profile" not in normalized:
            normalized["scanner_profile"] = normalized["scannerProfile"]
        if "scannerStrength" in normalized and "scanner_strength" not in normalized:
            normalized["scanner_strength"] = normalized["scannerStrength"]
        result = original_from_dict(normalized)
        result.scanner_profile = canonical_scanner_profile(normalized.get("scanner_profile"))
        try:
            scanner_strength = float(normalized.get("scanner_strength", 1.0))
        except (TypeError, ValueError):
            scanner_strength = 1.0
        result.scanner_strength = float(np.clip(scanner_strength, 0.0, 2.5))
        return result.sanitized()

    profiles = dict(FILM_PROFILES)
    for alias, target in FILM_PROFILE_ALIASES.items():
        profiles[alias] = FILM_PROFILES[target]
    engine.PROFILES.clear()
    engine.PROFILES.update(profiles)
    engine.FILM_PROFILES = FILM_PROFILES
    engine.SCANNER_PROFILES = SCANNER_PROFILES
    engine.FILM_PROFILE_ORDER = FILM_PROFILE_ORDER
    engine.SCANNER_PROFILE_ORDER = SCANNER_PROFILE_ORDER
    engine.canonical_film_profile = canonical_film_profile
    engine.canonical_scanner_profile = canonical_scanner_profile

    controls_class.sanitized = sanitized  # type: ignore[method-assign]
    controls_class.to_dict = to_dict  # type: ignore[method-assign]
    controls_class.from_dict = from_dict  # type: ignore[method-assign]
    controls_class._v060_style_library_applied = True  # type: ignore[attr-defined]

    engine.process_image = _process_image_v060
    engine.neutral_gains = _neutral_gains_v060
    processing.process_image = _process_image_v060

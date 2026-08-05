from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from . import engine, processing
from .core.lut import apply_cube_lut, load_cube_lut, resolve_user_lut, safe_lut_filename
from .storage.paths import default_lut_directory


def _process_with_user_lut(
    original_process: Any,
    image: np.ndarray,
    analysis: engine.Analysis,
    controls: engine.Controls | None = None,
) -> np.ndarray:
    current = (controls or engine.Controls()).sanitized()
    output = original_process(image, analysis, current)
    filename = safe_lut_filename(getattr(current, "user_lut", ""))
    if not filename:
        return output
    path = resolve_user_lut(default_lut_directory(), filename)
    if path is None or not path.is_file():
        return output
    try:
        lut = load_cube_lut(path)
        return apply_cube_lut(output, lut, float(current.style_strength))
    except (OSError, UnicodeError, ValueError):
        # Projects remain loadable even when a removable/custom LUT is missing
        # or invalid. The UI reports the missing file and lets the user replace it.
        return output


def apply_user_lut_engine_patch() -> None:
    """Persist and render a per-photo user .cube LUT after negative conversion."""

    controls_class = engine.Controls
    if getattr(controls_class, "_v072_user_lut_applied", False):
        return

    original_sanitized = controls_class.sanitized
    original_to_dict = controls_class.to_dict
    original_from_dict = controls_class.from_dict
    original_process = engine.process_image

    def sanitized(self: engine.Controls) -> engine.Controls:
        result = original_sanitized(self)
        result.user_lut = safe_lut_filename(getattr(self, "user_lut", ""))
        return result

    def to_dict(self: engine.Controls) -> dict[str, Any]:
        payload = dict(original_to_dict(self))
        payload["user_lut"] = safe_lut_filename(getattr(self, "user_lut", ""))
        return payload

    @classmethod
    def from_dict(cls: type[engine.Controls], value: Mapping[str, Any] | None) -> engine.Controls:
        normalized = dict(value or {})
        if "userLut" in normalized and "user_lut" not in normalized:
            normalized["user_lut"] = normalized["userLut"]
        result = original_from_dict(normalized)
        result.user_lut = safe_lut_filename(normalized.get("user_lut"))
        return result.sanitized()

    def process_image(
        image: np.ndarray,
        analysis: engine.Analysis,
        controls: engine.Controls | None = None,
    ) -> np.ndarray:
        return _process_with_user_lut(original_process, image, analysis, controls)

    def neutral_gains(
        image: np.ndarray,
        analysis: engine.Analysis,
        controls: engine.Controls,
        x: int,
        y: int,
        size: int = 11,
    ) -> tuple[float, float, float]:
        patch = engine.sample_patch(image, x, y, size)
        processed = process_image(patch, analysis, controls)
        average = np.median(processed.reshape(-1, 3), axis=0)
        target = float(np.clip(average @ np.array([0.2126, 0.7152, 0.0722]), 0.05, 0.95))
        current = controls.sanitized()
        gains = np.asarray(
            [current.red_gain, current.green_gain, current.blue_gain],
            dtype=np.float32,
        )
        gains *= target / np.maximum(average, 0.01)
        gains = np.clip(gains, 0.25, 3.0)
        return tuple(float(value) for value in gains)

    controls_class.sanitized = sanitized  # type: ignore[method-assign]
    controls_class.to_dict = to_dict  # type: ignore[method-assign]
    controls_class.from_dict = from_dict  # type: ignore[method-assign]
    controls_class._v072_user_lut_applied = True  # type: ignore[attr-defined]

    engine.process_image = process_image
    engine.neutral_gains = neutral_gains
    processing.process_image = process_image
    engine.default_lut_directory = default_lut_directory
    engine.safe_lut_filename = safe_lut_filename

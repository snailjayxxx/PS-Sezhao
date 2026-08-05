from __future__ import annotations

from typing import Any

import numpy as np

from .engine import Controls, PROFILES


def _wide_sanitized(self: Controls) -> Controls:
    """Sanitize controls while allowing a full ±255/255 base offset."""

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
        base_adjust=tuple(float(np.clip(value, -1.0, 1.0)) for value in self.base_adjust),
    )


def apply_engine_patch() -> None:
    if getattr(Controls, "_v053_wide_base_applied", False):
        return
    Controls.sanitized = _wide_sanitized  # type: ignore[method-assign]
    Controls._v053_wide_base_applied = True  # type: ignore[attr-defined]

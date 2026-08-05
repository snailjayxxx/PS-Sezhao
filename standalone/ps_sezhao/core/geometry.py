from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable, Mapping

import numpy as np

IDENTITY_PERSPECTIVE = (
    (0.0, 0.0),
    (1.0, 0.0),
    (1.0, 1.0),
    (0.0, 1.0),
)


@dataclass(frozen=True)
class GeometrySettings:
    straighten: float = 0.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    perspective: tuple[tuple[float, float], ...] = IDENTITY_PERSPECTIVE
    detection_confidence: float = 0.0
    detection_method: str = ""

    def sanitized(self) -> "GeometrySettings":
        return GeometrySettings(
            straighten=float(np.clip(float(self.straighten), -45.0, 45.0)),
            flip_horizontal=bool(self.flip_horizontal),
            flip_vertical=bool(self.flip_vertical),
            perspective=normalize_perspective(self.perspective),
            detection_confidence=float(np.clip(float(self.detection_confidence), 0.0, 1.0)),
            detection_method=str(self.detection_method or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self.sanitized())
        payload["perspective"] = [list(point) for point in self.sanitized().perspective]
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "GeometrySettings":
        if not value:
            return cls()
        return cls(
            straighten=_finite(value.get("straighten"), 0.0),
            flip_horizontal=bool(value.get("flip_horizontal", value.get("flipHorizontal", False))),
            flip_vertical=bool(value.get("flip_vertical", value.get("flipVertical", False))),
            perspective=normalize_perspective(value.get("perspective")),
            detection_confidence=_finite(
                value.get("detection_confidence", value.get("detectionConfidence")),
                0.0,
            ),
            detection_method=str(value.get("detection_method", value.get("detectionMethod", "")) or ""),
        ).sanitized()

    @property
    def is_identity(self) -> bool:
        return (
            abs(self.straighten) < 1e-6
            and not self.flip_horizontal
            and not self.flip_vertical
            and perspective_is_identity(self.perspective)
        )


@dataclass(frozen=True)
class FrameDetection:
    crop: tuple[float, float, float, float]
    confidence: float
    method: str
    used_fallback: bool


def _finite(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return parsed if math.isfinite(parsed) else float(fallback)


def normalize_perspective(value: Any) -> tuple[tuple[float, float], ...]:
    try:
        points = tuple(tuple(point) for point in value)
    except (TypeError, ValueError):
        return IDENTITY_PERSPECTIVE
    if len(points) != 4 or any(len(point) != 2 for point in points):
        return IDENTITY_PERSPECTIVE
    normalized: list[tuple[float, float]] = []
    for point in points:
        x = float(np.clip(_finite(point[0], 0.0), 0.0, 1.0))
        y = float(np.clip(_finite(point[1], 0.0), 0.0, 1.0))
        normalized.append((x, y))
    candidate = tuple(normalized)
    if _quad_area(candidate) < 0.01:
        return IDENTITY_PERSPECTIVE
    return candidate


def perspective_is_identity(
    perspective: Iterable[Iterable[float]] | None,
    *,
    tolerance: float = 1e-6,
) -> bool:
    points = normalize_perspective(perspective)
    return all(
        abs(point[0] - expected[0]) <= tolerance
        and abs(point[1] - expected[1]) <= tolerance
        for point, expected in zip(points, IDENTITY_PERSPECTIVE)
    )


def rotate_geometry(
    settings: GeometrySettings | Mapping[str, Any] | None,
    clockwise_degrees: int,
) -> GeometrySettings:
    geometry = settings if isinstance(settings, GeometrySettings) else GeometrySettings.from_dict(settings)
    turns = int(round(float(clockwise_degrees) / 90.0)) % 4
    points = list(geometry.perspective)
    for _ in range(turns):
        points = [(1.0 - y, x) for x, y in points]
        points = [points[3], points[0], points[1], points[2]]
    flip_horizontal = geometry.flip_horizontal
    flip_vertical = geometry.flip_vertical
    if turns % 2:
        flip_horizontal, flip_vertical = flip_vertical, flip_horizontal
    return GeometrySettings(
        straighten=geometry.straighten,
        flip_horizontal=flip_horizontal,
        flip_vertical=flip_vertical,
        perspective=tuple(points),
        detection_confidence=geometry.detection_confidence,
        detection_method=geometry.detection_method,
    ).sanitized()


def apply_photo_geometry(
    image: np.ndarray,
    settings: GeometrySettings | Mapping[str, Any] | None,
) -> np.ndarray:
    geometry = settings if isinstance(settings, GeometrySettings) else GeometrySettings.from_dict(settings)
    geometry = geometry.sanitized()
    array = np.ascontiguousarray(np.asarray(image, dtype=np.float32))
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("几何处理需要 H×W×C 图像。")
    if geometry.flip_horizontal:
        array = np.flip(array, axis=1).copy()
    if geometry.flip_vertical:
        array = np.flip(array, axis=0).copy()
    if abs(geometry.straighten) >= 1e-6:
        array = rotate_same_canvas(array, geometry.straighten)
    if not perspective_is_identity(geometry.perspective):
        array = warp_quad_to_rectangle(array, geometry.perspective)
    return np.ascontiguousarray(array, dtype=np.float32)


def rotate_same_canvas(image: np.ndarray, clockwise_degrees: float) -> np.ndarray:
    array = np.asarray(image, dtype=np.float32)
    height, width = array.shape[:2]
    angle = math.radians(float(clockwise_degrees))
    cosine = math.cos(angle)
    sine = math.sin(angle)
    center_x = (width - 1) / 2.0
    center_y = (height - 1) / 2.0

    # Destination-to-source mapping for clockwise display rotation.
    matrix = np.array(
        [
            [cosine, -sine, center_x - cosine * center_x + sine * center_y],
            [sine, cosine, center_y - sine * center_x - cosine * center_y],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    return _warp_homography(array, matrix, width, height)


def warp_quad_to_rectangle(
    image: np.ndarray,
    perspective: Iterable[Iterable[float]],
) -> np.ndarray:
    array = np.asarray(image, dtype=np.float32)
    height, width = array.shape[:2]
    points = normalize_perspective(perspective)
    source = np.asarray(
        [[x * (width - 1), y * (height - 1)] for x, y in points],
        dtype=np.float64,
    )
    top = np.linalg.norm(source[1] - source[0])
    bottom = np.linalg.norm(source[2] - source[3])
    left = np.linalg.norm(source[3] - source[0])
    right = np.linalg.norm(source[2] - source[1])
    output_width = int(np.clip(round(max(top, bottom)), 2, max(2, width * 2)))
    output_height = int(np.clip(round(max(left, right)), 2, max(2, height * 2)))
    destination = np.asarray(
        [
            [0.0, 0.0],
            [output_width - 1.0, 0.0],
            [output_width - 1.0, output_height - 1.0],
            [0.0, output_height - 1.0],
        ],
        dtype=np.float64,
    )
    destination_to_source = _homography(destination, source)
    return _warp_homography(array, destination_to_source, output_width, output_height)


def _homography(source: np.ndarray, destination: np.ndarray) -> np.ndarray:
    rows: list[list[float]] = []
    values: list[float] = []
    for (x, y), (u, v) in zip(source, destination):
        rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        values.append(u)
        rows.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        values.append(v)
    coefficients = np.linalg.solve(
        np.asarray(rows, dtype=np.float64),
        np.asarray(values, dtype=np.float64),
    )
    return np.asarray(
        [
            [coefficients[0], coefficients[1], coefficients[2]],
            [coefficients[3], coefficients[4], coefficients[5]],
            [coefficients[6], coefficients[7], 1.0],
        ],
        dtype=np.float64,
    )


def _warp_homography(
    image: np.ndarray,
    destination_to_source: np.ndarray,
    output_width: int,
    output_height: int,
    *,
    chunk_rows: int = 128,
) -> np.ndarray:
    array = np.asarray(image, dtype=np.float32)
    source_height, source_width, channels = array.shape
    output = np.zeros((output_height, output_width, channels), dtype=np.float32)
    x = np.arange(output_width, dtype=np.float64)[None, :]
    for top in range(0, output_height, max(8, int(chunk_rows))):
        bottom = min(output_height, top + max(8, int(chunk_rows)))
        y = np.arange(top, bottom, dtype=np.float64)[:, None]
        denominator = (
            destination_to_source[2, 0] * x
            + destination_to_source[2, 1] * y
            + destination_to_source[2, 2]
        )
        denominator = np.where(np.abs(denominator) < 1e-12, np.nan, denominator)
        source_x = (
            destination_to_source[0, 0] * x
            + destination_to_source[0, 1] * y
            + destination_to_source[0, 2]
        ) / denominator
        source_y = (
            destination_to_source[1, 0] * x
            + destination_to_source[1, 1] * y
            + destination_to_source[1, 2]
        ) / denominator
        output[top:bottom] = _sample_bilinear(
            array,
            source_x,
            source_y,
            source_width,
            source_height,
        )
    return output


def _sample_bilinear(
    image: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    width: int,
    height: int,
) -> np.ndarray:
    valid = np.isfinite(x) & np.isfinite(y) & (x >= 0.0) & (x <= width - 1) & (y >= 0.0) & (y <= height - 1)
    safe_x = np.where(valid, x, 0.0)
    safe_y = np.where(valid, y, 0.0)
    x0 = np.floor(safe_x).astype(np.int64)
    y0 = np.floor(safe_y).astype(np.int64)
    x1 = np.minimum(width - 1, x0 + 1)
    y1 = np.minimum(height - 1, y0 + 1)
    wx = (safe_x - x0)[..., None].astype(np.float32)
    wy = (safe_y - y0)[..., None].astype(np.float32)
    top = image[y0, x0] * (1.0 - wx) + image[y0, x1] * wx
    bottom = image[y1, x0] * (1.0 - wx) + image[y1, x1] * wx
    sampled = top * (1.0 - wy) + bottom * wy
    sampled[~valid] = 0.0
    return sampled.astype(np.float32, copy=False)


def detect_frame_bounds(
    image: np.ndarray,
    *,
    minimum_confidence: float = 0.30,
    max_edge: int = 360,
) -> FrameDetection:
    array = np.asarray(image, dtype=np.float32)
    if array.ndim != 3 or array.shape[0] < 12 or array.shape[1] < 12:
        return FrameDetection((0.0, 0.0, 1.0, 1.0), 0.0, "safe-full-frame", True)
    small = _downsample_for_detection(array, max_edge=max_edge)
    gray = small[..., 0] * 0.2126 + small[..., 1] * 0.7152 + small[..., 2] * 0.0722
    gray = _box_blur(gray, radius=2)
    gradient_x = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gradient_y = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    column_score = np.mean(gradient_x, axis=0)
    row_score = np.mean(gradient_y, axis=1)
    height, width = gray.shape

    left, left_quality = _edge_peak(column_score, 0.02, 0.43, reverse=False)
    right, right_quality = _edge_peak(column_score, 0.57, 0.98, reverse=True)
    top, top_quality = _edge_peak(row_score, 0.02, 0.43, reverse=False)
    bottom, bottom_quality = _edge_peak(row_score, 0.57, 0.98, reverse=True)

    crop = (
        float(left / max(1, width - 1)),
        float(top / max(1, height - 1)),
        float(right / max(1, width - 1)),
        float(bottom / max(1, height - 1)),
    )
    crop_width = crop[2] - crop[0]
    crop_height = crop[3] - crop[1]
    area = crop_width * crop_height
    geometry_quality = float(np.clip((min(crop_width, crop_height) - 0.25) / 0.45, 0.0, 1.0))
    area_quality = float(np.clip((area - 0.18) / 0.55, 0.0, 1.0))
    edge_quality = float(np.mean([left_quality, right_quality, top_quality, bottom_quality]))
    confidence = float(np.clip(edge_quality * 0.72 + geometry_quality * 0.14 + area_quality * 0.14, 0.0, 1.0))

    if crop_width < 0.30 or crop_height < 0.30 or confidence < minimum_confidence:
        return FrameDetection((0.0, 0.0, 1.0, 1.0), confidence, "safe-full-frame", True)
    margin = 1.0 / max(width, height)
    safe_crop = (
        max(0.0, crop[0] - margin),
        max(0.0, crop[1] - margin),
        min(1.0, crop[2] + margin),
        min(1.0, crop[3] + margin),
    )
    return FrameDetection(safe_crop, confidence, "gradient-projection", False)


def _edge_peak(
    score: np.ndarray,
    start_fraction: float,
    end_fraction: float,
    *,
    reverse: bool,
) -> tuple[int, float]:
    length = int(score.shape[0])
    start = max(1, min(length - 2, int(round(length * start_fraction))))
    end = max(start + 1, min(length - 1, int(round(length * end_fraction))))
    region = np.asarray(score[start:end], dtype=np.float64)
    if region.size == 0:
        return (end if reverse else start), 0.0
    peak_local = int(np.argmax(region))
    peak = float(region[peak_local])
    median = float(np.median(region))
    high = float(np.percentile(region, 95))
    denominator = max(1e-8, high - median)
    quality = float(np.clip((peak - median) / denominator, 0.0, 1.0))
    index = start + peak_local
    return index, quality


def _downsample_for_detection(image: np.ndarray, *, max_edge: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(1.0, float(max_edge) / max(height, width))
    if scale >= 0.999:
        return image[..., :3].astype(np.float32, copy=False)
    output_height = max(8, int(round(height * scale)))
    output_width = max(8, int(round(width * scale)))
    y = np.linspace(0, height - 1, output_height).astype(np.int64)
    x = np.linspace(0, width - 1, output_width).astype(np.int64)
    return image[np.ix_(y, x, np.arange(3))].astype(np.float32, copy=False)


def _box_blur(image: np.ndarray, *, radius: int) -> np.ndarray:
    radius = max(0, int(radius))
    if radius == 0:
        return image
    padded = np.pad(image, radius, mode="edge")
    output = np.zeros_like(image, dtype=np.float32)
    size = radius * 2 + 1
    for offset_y in range(size):
        for offset_x in range(size):
            output += padded[
                offset_y : offset_y + image.shape[0],
                offset_x : offset_x + image.shape[1],
            ]
    return output / float(size * size)


def _quad_area(points: Iterable[Iterable[float]]) -> float:
    values = list(points)
    if len(values) != 4:
        return 0.0
    total = 0.0
    for index, current in enumerate(values):
        following = values[(index + 1) % len(values)]
        total += float(current[0]) * float(following[1]) - float(following[0]) * float(current[1])
    return abs(total) * 0.5

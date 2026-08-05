from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Iterable

import numpy as np


SUPPORTED_LUT_SUFFIXES = (".cube",)


@dataclass(frozen=True)
class CubeLut:
    path: Path
    title: str
    dimension: int
    size: int
    table: np.ndarray
    domain_min: np.ndarray
    domain_max: np.ndarray


_CACHE_LOCK = RLock()
_CACHE: dict[tuple[str, int, int], CubeLut] = {}


def safe_lut_filename(value: str | Path | None) -> str:
    if not value:
        return ""
    name = Path(str(value)).name.strip()
    if Path(name).suffix.lower() not in SUPPORTED_LUT_SUFFIXES:
        return ""
    return name


def list_cube_luts(directory: str | Path) -> tuple[Path, ...]:
    root = Path(directory)
    if not root.is_dir():
        return ()
    return tuple(
        sorted(
            (
                path
                for path in root.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_LUT_SUFFIXES
            ),
            key=lambda path: path.name.casefold(),
        )
    )


def resolve_user_lut(directory: str | Path, filename: str | Path | None) -> Path | None:
    name = safe_lut_filename(filename)
    if not name:
        return None
    root = Path(directory).expanduser().resolve(strict=False)
    candidate = (root / name).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _parse_triplet(parts: list[str], directive: str) -> np.ndarray:
    if len(parts) != 4:
        raise ValueError(f"{directive} 必须包含三个数值。")
    try:
        return np.asarray([float(value) for value in parts[1:]], dtype=np.float32)
    except ValueError as exc:
        raise ValueError(f"{directive} 包含无效数值。") from exc


def parse_cube_lut(path: str | Path) -> CubeLut:
    source = Path(path).expanduser().resolve(strict=False)
    if source.suffix.lower() != ".cube":
        raise ValueError("当前仅支持 .cube LUT。")
    if not source.is_file():
        raise FileNotFoundError(source)

    title = source.stem
    size_1d: int | None = None
    size_3d: int | None = None
    domain_min = np.zeros(3, dtype=np.float32)
    domain_max = np.ones(3, dtype=np.float32)
    rows: list[tuple[float, float, float]] = []

    for line_number, raw_line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        directive = parts[0].upper()
        if directive == "TITLE":
            value = line[len(parts[0]) :].strip()
            title = value.strip('"') or source.stem
            continue
        if directive == "LUT_1D_SIZE":
            if len(parts) != 2:
                raise ValueError(f"第 {line_number} 行的 LUT_1D_SIZE 无效。")
            size_1d = int(parts[1])
            continue
        if directive == "LUT_3D_SIZE":
            if len(parts) != 2:
                raise ValueError(f"第 {line_number} 行的 LUT_3D_SIZE 无效。")
            size_3d = int(parts[1])
            continue
        if directive == "DOMAIN_MIN":
            domain_min = _parse_triplet(parts, directive)
            continue
        if directive == "DOMAIN_MAX":
            domain_max = _parse_triplet(parts, directive)
            continue
        if directive.startswith("LUT_"):
            # Unsupported metadata directives must not be mistaken for samples.
            continue
        if len(parts) < 3:
            raise ValueError(f"第 {line_number} 行不是有效的 RGB LUT 数据。")
        try:
            rows.append((float(parts[0]), float(parts[1]), float(parts[2])))
        except ValueError as exc:
            raise ValueError(f"第 {line_number} 行包含无效 LUT 数值。") from exc

    if size_1d and size_3d:
        raise ValueError("同一个 .cube 文件不能同时声明 1D 和 3D LUT。")
    dimension = 3 if size_3d is not None else 1
    size = int(size_3d or size_1d or 0)
    if size < 2 or size > 256:
        raise ValueError("LUT 尺寸必须在 2 到 256 之间。")
    if np.any(domain_max <= domain_min):
        raise ValueError("DOMAIN_MAX 必须逐通道大于 DOMAIN_MIN。")

    expected = size**3 if dimension == 3 else size
    if len(rows) != expected:
        raise ValueError(f"LUT 声明需要 {expected} 行 RGB 数据，实际为 {len(rows)} 行。")

    values = np.asarray(rows, dtype=np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError("LUT 包含 NaN 或无穷数值。")
    if dimension == 3:
        # The .cube convention changes red fastest, then green, then blue.
        table = values.reshape(size, size, size, 3)
    else:
        table = values.reshape(size, 3)

    return CubeLut(
        path=source,
        title=title,
        dimension=dimension,
        size=size,
        table=table,
        domain_min=domain_min,
        domain_max=domain_max,
    )


def load_cube_lut(path: str | Path) -> CubeLut:
    source = Path(path).expanduser().resolve(strict=False)
    stat = source.stat()
    key = (str(source), int(stat.st_mtime_ns), int(stat.st_size))
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
    parsed = parse_cube_lut(source)
    with _CACHE_LOCK:
        stale = [existing for existing in _CACHE if existing[0] == str(source) and existing != key]
        for existing in stale:
            _CACHE.pop(existing, None)
        _CACHE[key] = parsed
    return parsed


def _apply_1d(flat: np.ndarray, lut: CubeLut) -> np.ndarray:
    scaled = flat * float(lut.size - 1)
    lower = np.floor(scaled).astype(np.int32)
    upper = np.minimum(lower + 1, lut.size - 1)
    fraction = scaled - lower
    output = np.empty_like(flat, dtype=np.float32)
    for channel in range(3):
        lo = lut.table[lower[:, channel], channel]
        hi = lut.table[upper[:, channel], channel]
        output[:, channel] = lo + (hi - lo) * fraction[:, channel]
    return output


def _apply_3d(flat: np.ndarray, lut: CubeLut) -> np.ndarray:
    scaled = flat * float(lut.size - 1)
    lower = np.floor(scaled).astype(np.int32)
    upper = np.minimum(lower + 1, lut.size - 1)
    fraction = scaled - lower

    r0, g0, b0 = lower[:, 0], lower[:, 1], lower[:, 2]
    r1, g1, b1 = upper[:, 0], upper[:, 1], upper[:, 2]
    fr = fraction[:, 0:1]
    fg = fraction[:, 1:2]
    fb = fraction[:, 2:3]
    table = lut.table

    c000 = table[b0, g0, r0]
    c100 = table[b0, g0, r1]
    c010 = table[b0, g1, r0]
    c110 = table[b0, g1, r1]
    c001 = table[b1, g0, r0]
    c101 = table[b1, g0, r1]
    c011 = table[b1, g1, r0]
    c111 = table[b1, g1, r1]

    c00 = c000 + (c100 - c000) * fr
    c10 = c010 + (c110 - c010) * fr
    c01 = c001 + (c101 - c001) * fr
    c11 = c011 + (c111 - c011) * fr
    c0 = c00 + (c10 - c00) * fg
    c1 = c01 + (c11 - c01) * fg
    return c0 + (c1 - c0) * fb


def apply_cube_lut(image: np.ndarray, lut: CubeLut, strength: float = 1.0) -> np.ndarray:
    source = np.asarray(image, dtype=np.float32)
    if source.ndim < 2 or source.shape[-1] != 3:
        raise ValueError("LUT 输入必须是最后一维为 RGB 的数组。")
    amount = float(np.clip(strength, 0.0, 2.5))
    if amount <= 0.0:
        return source.copy()

    domain = np.maximum(lut.domain_max - lut.domain_min, 1e-8)
    normalized = np.clip((source - lut.domain_min) / domain, 0.0, 1.0)
    flat = normalized.reshape(-1, 3)
    mapped = _apply_3d(flat, lut) if lut.dimension == 3 else _apply_1d(flat, lut)
    mapped = mapped.reshape(source.shape)
    output = source + (mapped - source) * amount
    return np.clip(output, 0.0, 1.0).astype(np.float32)


def validate_cube_luts(paths: Iterable[str | Path]) -> tuple[CubeLut, ...]:
    return tuple(load_cube_lut(path) for path in paths)

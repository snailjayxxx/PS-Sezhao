from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from ..engine import Controls, analyze_image, process_image
from ..io_utils import load_image, make_preview
from ..raw_io import RawDecodeSettings, is_raw_path
from ..services.import_service import collect_supported_paths
from ..services.proxy_service import load_edit_proxy_frame, load_thumbnail_frame


@dataclass(frozen=True)
class RealRollItemReport:
    path: str
    suffix: str
    source_bytes: int
    raw: bool
    thumbnail_seconds: float | None
    proxy_seconds: float | None
    full_decode_seconds: float | None
    thumbnail_shape: tuple[int, ...] | None
    proxy_shape: tuple[int, ...] | None
    full_shape: tuple[int, ...] | None
    full_dtype: str | None
    analysis_confidence: float | None
    analysis_method: str | None
    output_min: float | None
    output_max: float | None
    output_mean: float | None
    metadata: dict[str, Any]
    review_image: str | None
    warnings: tuple[str, ...]
    error: str | None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class RealRollReport:
    created_at: str
    input_paths: tuple[str, ...]
    output_directory: str
    full_decode: bool
    total: int
    succeeded: int
    failed: int
    warnings: int
    elapsed_seconds: float
    items: tuple[RealRollItemReport, ...]

    @property
    def ok(self) -> bool:
        return self.total > 0 and self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ok"] = self.ok
        payload["items"] = [
            {
                **asdict(item),
                "ok": item.ok,
            }
            for item in self.items
        ]
        return payload

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return destination

    def write_markdown(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# PS-Sezhao 真实胶卷验证报告",
            "",
            f"- 创建时间：{self.created_at}",
            f"- 图片总数：{self.total}",
            f"- 成功：{self.succeeded}",
            f"- 失败：{self.failed}",
            f"- 含警告图片：{self.warnings}",
            f"- 完整解码：{'是' if self.full_decode else '否'}",
            f"- 总耗时：{self.elapsed_seconds:.2f} 秒",
            f"- 结论：{'通过' if self.ok else '未通过'}",
            "",
            "| 文件 | 类型 | 缩略图 | 编辑代理 | 完整解码 | 分析可信度 | 结果 |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
        for item in self.items:
            confidence = "-" if item.analysis_confidence is None else f"{item.analysis_confidence * 100:.0f}%"
            result = "失败" if item.error else ("警告" if item.warnings else "通过")
            lines.append(
                "| "
                + " | ".join(
                    (
                        Path(item.path).name.replace("|", "_"),
                        item.suffix,
                        _seconds(item.thumbnail_seconds),
                        _seconds(item.proxy_seconds),
                        _seconds(item.full_decode_seconds),
                        confidence,
                        result,
                    )
                )
                + " |"
            )
        problems = [item for item in self.items if item.error or item.warnings]
        if problems:
            lines.extend(("", "## 需要检查"))
            for item in problems:
                lines.append(f"\n### {Path(item.path).name}")
                if item.error:
                    lines.append(f"- 错误：{item.error}")
                for warning in item.warnings:
                    lines.append(f"- 警告：{warning}")
                if item.review_image:
                    lines.append(f"- 审阅图：`{item.review_image}`")
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return destination


def validate_real_roll(
    inputs: Iterable[str | Path],
    output_directory: str | Path,
    *,
    recursive: bool = True,
    max_files: int | None = None,
    full_decode: bool = True,
    raw_settings: RawDecodeSettings | Mapping[str, Any] | None = None,
    controls: Controls | Mapping[str, Any] | None = None,
) -> RealRollReport:
    """Validate real negative scans without modifying any source file."""

    started = time.perf_counter()
    input_paths = tuple(str(Path(value).expanduser()) for value in inputs)
    output_root = Path(output_directory).expanduser()
    review_root = output_root / "review"
    review_root.mkdir(parents=True, exist_ok=True)

    discovered = collect_supported_paths(
        [Path(value) for value in input_paths],
        recursive=recursive,
    )
    if max_files is not None:
        discovered = discovered[: max(0, int(max_files))]
    if not discovered:
        raise ValueError("没有找到可验证的图像或 RAW 文件。")

    decode_settings = (
        raw_settings
        if isinstance(raw_settings, RawDecodeSettings)
        else RawDecodeSettings.from_dict(raw_settings)
    )
    output_controls = controls if isinstance(controls, Controls) else Controls.from_dict(controls)
    reports = [
        _validate_one(
            path,
            review_root,
            full_decode=full_decode,
            raw_settings=decode_settings,
            controls=output_controls,
            index=index,
        )
        for index, path in enumerate(discovered, start=1)
    ]
    succeeded = sum(item.ok for item in reports)
    warning_count = sum(bool(item.warnings) for item in reports)
    return RealRollReport(
        created_at=datetime.now(timezone.utc).isoformat(),
        input_paths=input_paths,
        output_directory=str(output_root.resolve(strict=False)),
        full_decode=bool(full_decode),
        total=len(reports),
        succeeded=succeeded,
        failed=len(reports) - succeeded,
        warnings=warning_count,
        elapsed_seconds=round(time.perf_counter() - started, 6),
        items=tuple(reports),
    )


def _validate_one(
    path: Path,
    review_root: Path,
    *,
    full_decode: bool,
    raw_settings: RawDecodeSettings,
    controls: Controls,
    index: int,
) -> RealRollItemReport:
    warnings: list[str] = []
    metadata: dict[str, Any] = {}
    thumbnail_seconds = proxy_seconds = full_seconds = None
    thumbnail_shape = proxy_shape = full_shape = None
    full_dtype = None
    confidence = None
    analysis_method = None
    output_min = output_max = output_mean = None
    review_image = None
    try:
        source_bytes = path.stat().st_size
        started = time.perf_counter()
        thumbnail = load_thumbnail_frame(path, raw_settings)
        thumbnail_seconds = time.perf_counter() - started
        thumbnail_shape = tuple(int(value) for value in thumbnail.image.shape)
        _validate_array(thumbnail.image, "缩略图")
        metadata.update(_json_safe_mapping(thumbnail.metadata, prefix="thumbnail"))

        started = time.perf_counter()
        proxy = load_edit_proxy_frame(path, raw_settings)
        proxy_seconds = time.perf_counter() - started
        proxy_shape = tuple(int(value) for value in proxy.image.shape)
        _validate_array(proxy.image, "编辑代理")
        metadata.update(_json_safe_mapping(proxy.metadata, prefix="proxy"))

        analysis = analyze_image(proxy.image, border_fraction=0.07)
        confidence = float(analysis.confidence)
        analysis_method = str(analysis.method)
        if confidence < 0.45:
            warnings.append("自动胶片基底分析可信度低于 45%，应人工检查边框或使用基底吸管。")

        processed = process_image(proxy.image, analysis, controls)
        _validate_array(processed, "转正结果")
        output_min = float(np.min(processed))
        output_max = float(np.max(processed))
        output_mean = float(np.mean(processed))
        if output_max - output_min < 0.08:
            warnings.append("转正结果动态范围过窄，可能需要检查基底分析或原图曝光。")
        if output_mean < 0.03 or output_mean > 0.97:
            warnings.append("转正结果平均亮度接近极端值，可能存在曝光或基底问题。")

        if full_decode:
            started = time.perf_counter()
            full, full_metadata = load_image(path, raw_settings=raw_settings)
            full_seconds = time.perf_counter() - started
            _validate_array(full, "完整解码")
            full_shape = tuple(int(value) for value in full.shape)
            full_dtype = str(full.dtype)
            metadata.update(_json_safe_mapping(full_metadata, prefix="full"))
            full_preview = make_preview(full, 1800)
            full_processed = process_image(full_preview, analysis, controls)
            _validate_array(full_processed, "完整解码转正预览")

        review_path = review_root / f"{index:04d}-{_safe_stem(path.stem)}.jpg"
        _write_review_image(thumbnail.image, processed, review_path, path.name, confidence)
        review_image = str(review_path.resolve(strict=False))
        return RealRollItemReport(
            path=str(path.resolve(strict=False)),
            suffix=path.suffix.lower(),
            source_bytes=source_bytes,
            raw=is_raw_path(path),
            thumbnail_seconds=_rounded(thumbnail_seconds),
            proxy_seconds=_rounded(proxy_seconds),
            full_decode_seconds=_rounded(full_seconds),
            thumbnail_shape=thumbnail_shape,
            proxy_shape=proxy_shape,
            full_shape=full_shape,
            full_dtype=full_dtype,
            analysis_confidence=confidence,
            analysis_method=analysis_method,
            output_min=output_min,
            output_max=output_max,
            output_mean=output_mean,
            metadata=metadata,
            review_image=review_image,
            warnings=tuple(warnings),
            error=None,
        )
    except Exception as exc:
        try:
            source_bytes = path.stat().st_size
        except OSError:
            source_bytes = 0
        return RealRollItemReport(
            path=str(path.resolve(strict=False)),
            suffix=path.suffix.lower(),
            source_bytes=source_bytes,
            raw=is_raw_path(path),
            thumbnail_seconds=_rounded(thumbnail_seconds),
            proxy_seconds=_rounded(proxy_seconds),
            full_decode_seconds=_rounded(full_seconds),
            thumbnail_shape=thumbnail_shape,
            proxy_shape=proxy_shape,
            full_shape=full_shape,
            full_dtype=full_dtype,
            analysis_confidence=confidence,
            analysis_method=analysis_method,
            output_min=output_min,
            output_max=output_max,
            output_mean=output_mean,
            metadata=metadata,
            review_image=review_image,
            warnings=tuple(warnings),
            error=f"{type(exc).__name__}: {exc}",
        )


def _validate_array(image: np.ndarray, label: str) -> None:
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError(f"{label}不是有效 RGB 图像：shape={array.shape}")
    if array.shape[0] < 2 or array.shape[1] < 2:
        raise ValueError(f"{label}尺寸过小：shape={array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label}包含 NaN 或无穷值。")
    minimum = float(np.min(array))
    maximum = float(np.max(array))
    if minimum < -1e-4 or maximum > 1.0001:
        raise ValueError(f"{label}数值超出 0..1：{minimum:.6f}..{maximum:.6f}")


def _write_review_image(
    negative: np.ndarray,
    positive: np.ndarray,
    destination: Path,
    name: str,
    confidence: float,
) -> None:
    left = _array_to_pil(negative)
    right = _array_to_pil(positive)
    max_edge = 1200
    left.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    right.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    height = max(left.height, right.height)
    header = 42
    canvas = Image.new("RGB", (left.width + right.width, height + header), (24, 24, 24))
    canvas.paste(left, (0, header))
    canvas.paste(right, (left.width, header))
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), f"{name} · negative", fill=(235, 235, 235))
    draw.text((left.width + 10, 10), f"positive · confidence {confidence * 100:.0f}%", fill=(235, 235, 235))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="JPEG", quality=92, optimize=True)


def _array_to_pil(image: np.ndarray) -> Image.Image:
    array = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    return Image.fromarray(np.round(array[..., :3] * 255.0).astype(np.uint8), mode="RGB")


def _json_safe_mapping(value: Mapping[str, Any], *, prefix: str) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe[f"{prefix}.{key}"] = item
        elif isinstance(item, Path):
            safe[f"{prefix}.{key}"] = str(item)
        elif isinstance(item, (tuple, list)) and len(item) <= 16:
            safe[f"{prefix}.{key}"] = [
                value if isinstance(value, (str, int, float, bool)) or value is None else str(value)
                for value in item
            ]
    return safe


def _safe_stem(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_" else "_" for character in value)
    return cleaned[:80] or "image"


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _seconds(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}s"

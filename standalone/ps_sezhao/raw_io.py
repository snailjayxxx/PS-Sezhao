from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from PIL import Image, ImageOps

from .color_profiles import PROPHOTO_RGB_V2_MICRO, validate_profiles

try:  # Import lazily enough to keep a clear error for source-only installs.
    import rawpy  # type: ignore
except ImportError:  # pragma: no cover - exercised only when an optional install is incomplete.
    rawpy = None  # type: ignore


RAW_EXTENSIONS = {
    ".3fr",
    ".ari",
    ".arw",
    ".bay",
    ".cap",
    ".cr2",
    ".cr3",
    ".dcr",
    ".dng",
    ".erf",
    ".fff",
    ".gpr",
    ".iiq",
    ".k25",
    ".kdc",
    ".mef",
    ".mos",
    ".mrw",
    ".nef",
    ".nrw",
    ".orf",
    ".pef",
    ".ptx",
    ".pxn",
    ".raf",
    ".raw",
    ".rw2",
    ".rwl",
    ".sr2",
    ".srf",
    ".srw",
    ".x3f",
}

WB_MODES = {"camera", "daylight", "auto", "custom"}
HIGHLIGHT_MODES = {"clip", "blend", "reconstruct"}
DEMOSAIC_MODES = {"ahd", "linear", "vng", "ppg"}


class RawDecodeError(RuntimeError):
    """A user-facing RAW decode error with a practical fallback."""


@dataclass(frozen=True)
class RawDecodeSettings:
    """Settings used for deterministic film-negative RAW decoding.

    Full-size decoding is always 16-bit, linear, ProPhoto RGB and has LibRaw's
    automatic brightness disabled. These options only control white balance,
    demosaic/highlight handling and the fast preview path.
    """

    wb_mode: str = "camera"
    custom_wb: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    highlight_mode: str = "blend"
    demosaic: str = "ahd"
    use_embedded_preview: bool = True
    half_size_preview: bool = True

    def sanitized(self) -> "RawDecodeSettings":
        wb_mode = self.wb_mode if self.wb_mode in WB_MODES else "camera"
        highlight_mode = self.highlight_mode if self.highlight_mode in HIGHLIGHT_MODES else "blend"
        demosaic = self.demosaic if self.demosaic in DEMOSAIC_MODES else "ahd"
        values = list(self.custom_wb)[:4]
        while len(values) < 4:
            values.append(1.0)
        clean: list[float] = []
        for value in values:
            try:
                number = float(value)
            except (TypeError, ValueError):
                number = 1.0
            if not math.isfinite(number):
                number = 1.0
            clean.append(float(np.clip(number, 0.05, 16.0)))
        return RawDecodeSettings(
            wb_mode=wb_mode,
            custom_wb=tuple(clean),
            highlight_mode=highlight_mode,
            demosaic=demosaic,
            use_embedded_preview=bool(self.use_embedded_preview),
            half_size_preview=bool(self.half_size_preview),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self.sanitized())
        value["custom_wb"] = list(value["custom_wb"])
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "RawDecodeSettings":
        if not value:
            return cls()
        custom = value.get("custom_wb", (1.0, 1.0, 1.0, 1.0))
        if not isinstance(custom, (list, tuple)):
            custom = (1.0, 1.0, 1.0, 1.0)
        return cls(
            wb_mode=str(value.get("wb_mode", "camera")),
            custom_wb=tuple(custom),
            highlight_mode=str(value.get("highlight_mode", "blend")),
            demosaic=str(value.get("demosaic", "ahd")),
            use_embedded_preview=bool(value.get("use_embedded_preview", True)),
            half_size_preview=bool(value.get("half_size_preview", True)),
        ).sanitized()


def is_raw_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in RAW_EXTENSIONS


def raw_runtime_summary() -> str:
    if rawpy is None:
        return "RAW 组件不可用：安装包缺少 rawpy / LibRaw。"
    libraw = getattr(rawpy, "libraw_version", None)
    if isinstance(libraw, (tuple, list)):
        libraw_text = ".".join(str(part) for part in libraw)
    else:
        libraw_text = str(libraw or "未知")
    return f"rawpy {getattr(rawpy, '__version__', '未知')} · LibRaw {libraw_text}"


def _require_rawpy() -> Any:
    if rawpy is None:
        raise RawDecodeError(
            "当前程序没有包含 RAW 解码组件。请重新安装 PS-Sezhao 完整版；"
            "临时可在 Lightroom Classic、Camera Raw 或相机厂商软件中导出 16 位 TIFF。"
        )
    validate_profiles()
    return rawpy


def _enum_value(module: Any, settings: RawDecodeSettings) -> tuple[Any, Any]:
    highlight_map = {
        "clip": module.HighlightMode.Clip,
        "blend": module.HighlightMode.Blend,
        "reconstruct": module.HighlightMode.ReconstructDefault,
    }
    demosaic_map = {
        "ahd": module.DemosaicAlgorithm.AHD,
        "linear": module.DemosaicAlgorithm.LINEAR,
        "vng": module.DemosaicAlgorithm.VNG,
        "ppg": module.DemosaicAlgorithm.PPG,
    }
    algorithm = demosaic_map[settings.demosaic]
    supported = getattr(algorithm, "isSupported", True)
    if supported is False:
        algorithm = module.DemosaicAlgorithm.AHD
    return highlight_map[settings.highlight_mode], algorithm


def _wb_kwargs(settings: RawDecodeSettings) -> dict[str, Any]:
    if settings.wb_mode == "camera":
        return {"use_camera_wb": True, "use_auto_wb": False, "user_wb": None}
    if settings.wb_mode == "auto":
        return {"use_camera_wb": False, "use_auto_wb": True, "user_wb": None}
    if settings.wb_mode == "custom":
        return {
            "use_camera_wb": False,
            "use_auto_wb": False,
            "user_wb": list(settings.custom_wb),
        }
    # LibRaw uses its daylight coefficients when all WB switches are disabled.
    return {"use_camera_wb": False, "use_auto_wb": False, "user_wb": None}


def _safe_float_list(value: Any) -> list[float] | None:
    if value is None:
        return None
    try:
        result = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return [item if math.isfinite(item) else 0.0 for item in result]


def _unsupported_types(module: Any) -> tuple[type[BaseException], ...]:
    names = (
        "LibRawFileUnsupportedError",
        "LibRawNotImplementedError",
        "NotSupportedError",
    )
    values: list[type[BaseException]] = []
    for name in names:
        candidate = getattr(module, name, None)
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            values.append(candidate)
    return tuple(values)


def _decode_error(source: Path, module: Any, error: BaseException) -> RawDecodeError:
    unsupported = _unsupported_types(module)
    if unsupported and isinstance(error, unsupported):
        detail = "当前 LibRaw 不支持该相机型号、RAW 压缩方式或多帧结构"
    else:
        detail = "RAW 文件读取失败或文件数据不完整"
    return RawDecodeError(
        f"无法解码 RAW：{source.name}\n\n{detail}。\n"
        f"运行环境：{raw_runtime_summary()}\n"
        "可先用 Lightroom Classic、Camera Raw 或相机厂商软件导出 16 位 TIFF 后继续处理。"
    )


def decode_raw(
    path: str | Path,
    settings: RawDecodeSettings | Mapping[str, Any] | None = None,
    *,
    half_size: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Decode a camera RAW into 16-bit-equivalent linear ProPhoto RGB floats."""

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"找不到 RAW 文件：{source}")
    module = _require_rawpy()
    config = settings if isinstance(settings, RawDecodeSettings) else RawDecodeSettings.from_dict(settings)
    config = config.sanitized()
    highlight_mode, algorithm = _enum_value(module, config)

    try:
        with module.imread(str(source)) as raw:
            sizes = getattr(raw, "sizes", None)
            other = getattr(raw, "other", None)
            lens = getattr(raw, "lens", None)
            kwargs: dict[str, Any] = {
                "half_size": bool(half_size),
                "demosaic_algorithm": algorithm,
                "output_color": module.ColorSpace.ProPhoto,
                "output_bps": 16,
                "no_auto_bright": True,
                "gamma": (1.0, 1.0),
                "highlight_mode": highlight_mode,
            }
            kwargs.update(_wb_kwargs(config))
            rgb16 = raw.postprocess(**kwargs)
            metadata: dict[str, Any] = {
                "path": str(source),
                "icc_profile": PROPHOTO_RGB_V2_MICRO,
                "source_dtype": str(rgb16.dtype),
                "raw": True,
                "linear_raw": True,
                "raw_decode": config.to_dict(),
                "raw_runtime": raw_runtime_summary(),
                "camera_whitebalance": _safe_float_list(getattr(raw, "camera_whitebalance", None)),
                "daylight_whitebalance": _safe_float_list(getattr(raw, "daylight_whitebalance", None)),
                "white_level": int(getattr(raw, "white_level", 0) or 0),
                "black_level_per_channel": list(getattr(raw, "black_level_per_channel", []) or []),
                "raw_size": {
                    "raw_width": int(getattr(sizes, "raw_width", 0) or 0),
                    "raw_height": int(getattr(sizes, "raw_height", 0) or 0),
                    "width": int(getattr(sizes, "width", rgb16.shape[1]) or rgb16.shape[1]),
                    "height": int(getattr(sizes, "height", rgb16.shape[0]) or rgb16.shape[0]),
                },
                "capture": {
                    "iso": float(getattr(other, "iso_speed", 0.0) or 0.0),
                    "shutter": float(getattr(other, "shutter_speed", 0.0) or 0.0),
                    "aperture": float(getattr(other, "aperture", 0.0) or 0.0),
                    "focal_length": float(getattr(other, "focal_length", 0.0) or 0.0),
                },
                "lens": str(getattr(lens, "model", "") or ""),
            }
    except Exception as error:
        if isinstance(error, RawDecodeError):
            raise
        raise _decode_error(source, module, error) from error

    array = np.asarray(rgb16)
    if array.ndim == 2:
        array = np.repeat(array[..., None], 3, axis=2)
    if array.ndim != 3 or array.shape[2] < 3:
        raise RawDecodeError(f"RAW 解码结果结构无效：shape={array.shape}")
    result = array[..., :3].astype(np.float32) / 65535.0
    return np.clip(result, 0.0, 1.0), metadata


def _resize_preview(image: np.ndarray, max_edge: int) -> np.ndarray:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    height, width = rgb.shape[:2]
    if max(height, width) <= max_edge:
        return rgb.copy()
    scale = max_edge / float(max(height, width))
    target = (max(1, round(width * scale)), max(1, round(height * scale)))
    data8 = np.round(rgb * 255.0).astype(np.uint8)
    resized = Image.fromarray(data8, mode="RGB").resize(target, Image.Resampling.LANCZOS)
    return np.asarray(resized, dtype=np.float32) / 255.0


def extract_raw_preview(
    path: str | Path,
    settings: RawDecodeSettings | Mapping[str, Any] | None = None,
    *,
    max_edge: int = 1800,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return a fast display preview, preferring the RAW's embedded thumbnail."""

    source = Path(path)
    module = _require_rawpy()
    config = settings if isinstance(settings, RawDecodeSettings) else RawDecodeSettings.from_dict(settings)
    config = config.sanitized()

    if config.use_embedded_preview:
        try:
            with module.imread(str(source)) as raw:
                thumb = raw.extract_thumb()
            if thumb.format == module.ThumbFormat.JPEG:
                with Image.open(BytesIO(thumb.data)) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    preview = np.asarray(image, dtype=np.uint8).astype(np.float32) / 255.0
            elif thumb.format == module.ThumbFormat.BITMAP:
                data = np.asarray(thumb.data)
                if data.ndim == 2:
                    data = np.repeat(data[..., None], 3, axis=2)
                data = data[..., :3]
                if np.issubdtype(data.dtype, np.integer):
                    preview = data.astype(np.float32) / float(np.iinfo(data.dtype).max)
                else:
                    preview = np.clip(data.astype(np.float32), 0.0, 1.0)
            else:
                preview = None
            if preview is not None:
                return _resize_preview(preview, max_edge), {
                    "path": str(source),
                    "raw": True,
                    "preview_source": "embedded",
                    "raw_runtime": raw_runtime_summary(),
                }
        except Exception as error:
            unsupported = _unsupported_types(module)
            no_thumb_types = tuple(
                candidate
                for candidate in (
                    getattr(module, "LibRawNoThumbnailError", None),
                    getattr(module, "LibRawUnsupportedThumbnailError", None),
                )
                if isinstance(candidate, type) and issubclass(candidate, BaseException)
            )
            if unsupported and isinstance(error, unsupported):
                raise _decode_error(source, module, error) from error
            if no_thumb_types and not isinstance(error, no_thumb_types):
                # A corrupt embedded preview should not block full RAW decoding.
                pass

    image, metadata = decode_raw(source, config, half_size=config.half_size_preview)
    metadata = dict(metadata)
    metadata["preview_source"] = "half-size-decode" if config.half_size_preview else "full-decode"
    return _resize_preview(prepare_display_output(image, metadata), max_edge), metadata


def prepare_display_output(image: np.ndarray, metadata: Mapping[str, Any] | None) -> np.ndarray:
    """Create a monitor-friendly approximation for Tk/Pillow preview display."""

    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    if metadata and metadata.get("linear_raw"):
        # Tk does not color-manage the canvas. A simple display gamma keeps the
        # linear negative/positive visible while the saved TIFF remains tagged.
        return np.power(rgb, 1.0 / 2.2).astype(np.float32)
    return rgb


def prepare_save_output(image: np.ndarray, metadata: Mapping[str, Any] | None) -> np.ndarray:
    """Encode linear ProPhoto working data for the embedded gamma-1.8 profile."""

    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    if metadata and metadata.get("linear_raw"):
        return np.power(rgb, 1.0 / 1.8).astype(np.float32)
    return rgb

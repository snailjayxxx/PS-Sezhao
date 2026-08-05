from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image, ImageCms, ImageDraw, PngImagePlugin
import tifffile

from ..color_profiles import PROPHOTO_RGB_V2_MICRO


FORMAT_SPECS: dict[str, tuple[str, int, str]] = {
    "16 位 TIFF（无损）": (".tif", 16, "16 位 TIFF"),
    "8 位 TIFF（无损）": (".tif", 8, "8 位 TIFF"),
    "JPEG": (".jpg", 8, "JPEG"),
    "PNG（无损）": (".png", 8, "PNG"),
}
COLOR_SPACES = {"preserve", "prophoto", "srgb"}
RESIZE_MODES = {"original", "long_edge", "width", "height", "percent"}
RESAMPLE_MODES = {"lanczos", "bicubic", "bilinear", "nearest"}
SHARPEN_MODES = {"off", "low", "standard", "high"}
COLLISION_POLICIES = {"auto_number", "overwrite", "skip", "error"}
CONTACT_BACKGROUNDS = {"dark", "light"}

_INVALID_FILENAME = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")
_TOKEN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

try:
    SRGB_ICC_PROFILE = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
except Exception:  # pragma: no cover - Pillow builds without lcms are uncommon.
    SRGB_ICC_PROFILE = b""


@dataclass(frozen=True)
class OutputSettings:
    format_label: str = "16 位 TIFF（无损）"
    jpeg_quality: int = 95
    color_space: str = "prophoto"
    resize_mode: str = "original"
    resize_value: float = 3000.0
    allow_upscale: bool = False
    resample: str = "lanczos"
    sharpen: str = "off"
    filename_template: str = "{stem}_PS-Sezhao"
    collision_policy: str = "auto_number"
    embed_metadata: bool = True
    roll_name: str = ""
    film_stock: str = ""
    camera: str = ""
    capture_date: str = ""
    frame_number: str = ""
    note: str = ""
    contact_columns: int = 5
    contact_cell_size: int = 360
    contact_labels: bool = True
    contact_background: str = "dark"

    def sanitized(self) -> "OutputSettings":
        format_label = self.format_label if self.format_label in FORMAT_SPECS else "16 位 TIFF（无损）"
        try:
            quality = int(self.jpeg_quality)
        except (TypeError, ValueError):
            quality = 95
        try:
            resize_value = float(self.resize_value)
        except (TypeError, ValueError):
            resize_value = 3000.0
        if not math.isfinite(resize_value):
            resize_value = 3000.0
        try:
            columns = int(self.contact_columns)
        except (TypeError, ValueError):
            columns = 5
        try:
            cell_size = int(self.contact_cell_size)
        except (TypeError, ValueError):
            cell_size = 360
        template = str(self.filename_template or "").strip() or "{stem}_PS-Sezhao"
        return OutputSettings(
            format_label=format_label,
            jpeg_quality=min(100, max(1, quality)),
            color_space=self.color_space if self.color_space in COLOR_SPACES else "prophoto",
            resize_mode=self.resize_mode if self.resize_mode in RESIZE_MODES else "original",
            resize_value=min(100000.0, max(1.0, resize_value)),
            allow_upscale=bool(self.allow_upscale),
            resample=self.resample if self.resample in RESAMPLE_MODES else "lanczos",
            sharpen=self.sharpen if self.sharpen in SHARPEN_MODES else "off",
            filename_template=template[:240],
            collision_policy=self.collision_policy if self.collision_policy in COLLISION_POLICIES else "auto_number",
            embed_metadata=bool(self.embed_metadata),
            roll_name=_clean_metadata_text(self.roll_name),
            film_stock=_clean_metadata_text(self.film_stock),
            camera=_clean_metadata_text(self.camera),
            capture_date=_clean_metadata_text(self.capture_date),
            frame_number=_clean_metadata_text(self.frame_number),
            note=_clean_metadata_text(self.note, limit=1000),
            contact_columns=min(12, max(1, columns)),
            contact_cell_size=min(1200, max(120, cell_size)),
            contact_labels=bool(self.contact_labels),
            contact_background=self.contact_background if self.contact_background in CONTACT_BACKGROUNDS else "dark",
        )

    @property
    def extension(self) -> str:
        return FORMAT_SPECS[self.sanitized().format_label][0]

    @property
    def bit_depth(self) -> int:
        return FORMAT_SPECS[self.sanitized().format_label][1]

    @property
    def format_name(self) -> str:
        return FORMAT_SPECS[self.sanitized().format_label][2]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.sanitized())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "OutputSettings":
        if not value:
            return cls()
        fields = cls.__dataclass_fields__
        payload = {key: value[key] for key in fields if key in value}
        return cls(**payload).sanitized()


@dataclass(frozen=True)
class PreparedOutput:
    image: np.ndarray
    icc_profile: bytes | None
    metadata: dict[str, str]


@dataclass(frozen=True)
class ContactSheetEntry:
    image: np.ndarray
    label: str


def calculate_resize_dimensions(
    width: int,
    height: int,
    settings: OutputSettings | Mapping[str, Any] | None,
) -> tuple[int, int]:
    config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
    config = config.sanitized()
    width = max(1, int(width))
    height = max(1, int(height))
    if config.resize_mode == "original":
        return width, height
    value = float(config.resize_value)
    if config.resize_mode == "long_edge":
        scale = value / max(width, height)
    elif config.resize_mode == "width":
        scale = value / width
    elif config.resize_mode == "height":
        scale = value / height
    else:
        scale = value / 100.0
    if not config.allow_upscale:
        scale = min(1.0, scale)
    scale = max(1.0 / max(width, height), min(64.0, scale))
    return max(1, round(width * scale)), max(1, round(height * scale))


def resize_float_image(
    image: np.ndarray,
    settings: OutputSettings | Mapping[str, Any] | None,
) -> np.ndarray:
    config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
    config = config.sanitized()
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    height, width = rgb.shape[:2]
    target = calculate_resize_dimensions(width, height, config)
    if target == (width, height):
        return rgb.copy()
    filters = {
        "lanczos": Image.Resampling.LANCZOS,
        "bicubic": Image.Resampling.BICUBIC,
        "bilinear": Image.Resampling.BILINEAR,
        "nearest": Image.Resampling.NEAREST,
    }
    channels: list[np.ndarray] = []
    for channel in range(3):
        plane = Image.fromarray(rgb[..., channel], mode="F")
        plane = plane.resize(target, filters[config.resample])
        channels.append(np.asarray(plane, dtype=np.float32))
    return np.clip(np.stack(channels, axis=2), 0.0, 1.0)


def apply_output_sharpening(
    image: np.ndarray,
    mode: str,
) -> np.ndarray:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    if mode not in SHARPEN_MODES or mode == "off" or min(rgb.shape[:2]) < 3:
        return rgb.copy()
    amount = {"low": 0.35, "standard": 0.65, "high": 1.0}[mode]
    padded = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), mode="edge")
    blur = np.zeros_like(rgb)
    weights = (
        (1.0, 2.0, 1.0),
        (2.0, 4.0, 2.0),
        (1.0, 2.0, 1.0),
    )
    for y in range(3):
        for x in range(3):
            blur += padded[y : y + rgb.shape[0], x : x + rgb.shape[1]] * (weights[y][x] / 16.0)
    detail = rgb - blur
    detail[np.abs(detail) < 1.0 / 1024.0] = 0.0
    return np.clip(rgb + detail * amount, 0.0, 1.0).astype(np.float32)


def prepare_output(
    image: np.ndarray,
    settings: OutputSettings | Mapping[str, Any] | None,
    *,
    source_icc_profile: bytes | None = None,
    source_metadata: Mapping[str, Any] | None = None,
) -> PreparedOutput:
    config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
    config = config.sanitized()
    resized = resize_float_image(image, config)
    converted, profile = convert_color_space(
        resized,
        config.color_space,
        source_icc_profile=source_icc_profile,
        source_metadata=source_metadata,
    )
    sharpened = apply_output_sharpening(converted, config.sharpen)
    metadata = output_metadata(config, source_metadata=source_metadata)
    return PreparedOutput(sharpened, profile, metadata)


def convert_color_space(
    image: np.ndarray,
    color_space: str,
    *,
    source_icc_profile: bytes | None,
    source_metadata: Mapping[str, Any] | None = None,
) -> tuple[np.ndarray, bytes | None]:
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    if color_space == "preserve":
        return rgb.copy(), source_icc_profile
    if color_space == "prophoto":
        return rgb.copy(), PROPHOTO_RGB_V2_MICRO
    source_is_prophoto = bool(source_icc_profile == PROPHOTO_RGB_V2_MICRO)
    if source_metadata and source_metadata.get("linear_raw"):
        source_is_prophoto = True
    converted = _prophoto_to_srgb(rgb) if source_is_prophoto else rgb.copy()
    return converted, SRGB_ICC_PROFILE or None


def _prophoto_to_srgb(image: np.ndarray) -> np.ndarray:
    prophoto_to_xyz_d50 = np.asarray(
        (
            (0.7976749, 0.1351917, 0.0313534),
            (0.2880402, 0.7118741, 0.0000857),
            (0.0, 0.0, 0.8252100),
        ),
        dtype=np.float32,
    )
    d50_to_d65 = np.asarray(
        (
            (0.9555766, -0.0230393, 0.0631636),
            (-0.0282895, 1.0099416, 0.0210077),
            (0.0122982, -0.0204830, 1.3299098),
        ),
        dtype=np.float32,
    )
    xyz_to_srgb = np.asarray(
        (
            (3.2404542, -1.5371385, -0.4985314),
            (-0.9692660, 1.8760108, 0.0415560),
            (0.0556434, -0.2040259, 1.0572252),
        ),
        dtype=np.float32,
    )
    output = np.empty_like(image, dtype=np.float32)
    for top in range(0, image.shape[0], 512):
        block = np.clip(image[top : top + 512], 0.0, 1.0)
        linear = np.power(block, 1.8)
        flat = linear.reshape(-1, 3)
        xyz_d50 = flat @ prophoto_to_xyz_d50.T
        xyz_d65 = xyz_d50 @ d50_to_d65.T
        srgb_linear = xyz_d65 @ xyz_to_srgb.T
        srgb_linear = np.clip(srgb_linear, 0.0, 1.0)
        encoded = np.where(
            srgb_linear <= 0.0031308,
            srgb_linear * 12.92,
            1.055 * np.power(srgb_linear, 1.0 / 2.4) - 0.055,
        )
        output[top : top + block.shape[0]] = encoded.reshape(block.shape)
    return np.clip(output, 0.0, 1.0).astype(np.float32)


def render_filename(
    source: str | Path,
    settings: OutputSettings | Mapping[str, Any] | None,
    *,
    index: int,
    sequence: int,
    profile: str = "",
) -> str:
    config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
    config = config.sanitized()
    path = Path(source)
    values = {
        "stem": path.stem,
        "name": path.name,
        "index": str(index),
        "sequence": f"{sequence:04d}",
        "roll": config.roll_name,
        "film": config.film_stock,
        "camera": config.camera,
        "date": config.capture_date,
        "frame": config.frame_number or f"{sequence:04d}",
        "profile": profile,
    }

    def replace_token(match: re.Match[str]) -> str:
        return str(values.get(match.group(1), ""))

    rendered = _TOKEN.sub(replace_token, config.filename_template)
    rendered = _INVALID_FILENAME.sub("_", rendered)
    rendered = re.sub(r"\s+", " ", rendered).strip(" .")
    rendered = re.sub(r"_+", "_", rendered)
    if not rendered:
        rendered = f"{path.stem}_PS-Sezhao"
    return rendered[:180].rstrip(" .")


def resolve_destination(
    requested: str | Path,
    policy: str,
    reserved: set[str],
) -> Path | None:
    destination = Path(requested)
    policy = policy if policy in COLLISION_POLICIES else "auto_number"
    key = _destination_key(destination)
    if policy == "skip":
        if destination.exists() or key in reserved:
            return None
        reserved.add(key)
        return destination
    if policy == "error":
        if destination.exists() or key in reserved:
            raise FileExistsError(f"输出文件已存在：{destination}")
        reserved.add(key)
        return destination
    if policy == "overwrite":
        if key not in reserved:
            reserved.add(key)
            return destination
        return _numbered_destination(destination, reserved, check_existing=False)
    return _numbered_destination(destination, reserved, check_existing=True)


def _numbered_destination(
    requested: Path,
    reserved: set[str],
    *,
    check_existing: bool,
) -> Path:
    candidate = requested
    number = 2
    while _destination_key(candidate) in reserved or (check_existing and candidate.exists()):
        candidate = requested.with_name(f"{requested.stem}_{number}{requested.suffix}")
        number += 1
    reserved.add(_destination_key(candidate))
    return candidate


def _destination_key(path: Path) -> str:
    return str(Path(path).expanduser().resolve(strict=False)).casefold()


def output_metadata(
    settings: OutputSettings | Mapping[str, Any] | None,
    *,
    source_metadata: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
    config = config.sanitized()
    if not config.embed_metadata:
        return {}
    metadata = {
        "Software": "PS-Sezhao",
        "Roll": config.roll_name,
        "FilmStock": config.film_stock,
        "Camera": config.camera,
        "CaptureDate": config.capture_date,
        "FrameNumber": config.frame_number,
        "Note": config.note,
    }
    if source_metadata:
        source = source_metadata.get("path")
        if source:
            metadata["SourceFile"] = Path(str(source)).name
    return {key: value for key, value in metadata.items() if value}


def save_output_file(
    path: str | Path,
    image: np.ndarray,
    *,
    bit_depth: int,
    icc_profile: bytes | None,
    jpeg_quality: int,
    metadata: Mapping[str, str] | None = None,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    suffix = destination.suffix.lower()
    metadata_payload = {str(key): str(value) for key, value in (metadata or {}).items() if value}
    description = json.dumps(metadata_payload, ensure_ascii=True, sort_keys=True) if metadata_payload else ""
    capture_date = _exif_datetime(metadata_payload.get("CaptureDate", ""))

    if suffix in {".tif", ".tiff"}:
        data = (
            np.round(rgb * 65535.0).astype(np.uint16)
            if int(bit_depth) >= 16
            else np.round(rgb * 255.0).astype(np.uint8)
        )
        extra_tags = None
        if icc_profile:
            extra_tags = [(34675, "B", len(icc_profile), bytes(icc_profile), False)]
        tifffile.imwrite(
            destination,
            data,
            photometric="rgb",
            metadata=None,
            compression="zlib",
            description=description or None,
            datetime=capture_date or None,
            software="PS-Sezhao",
            extratags=extra_tags,
        )
        return destination

    data8 = np.round(rgb * 255.0).astype(np.uint8)
    pil_image = Image.fromarray(data8, mode="RGB")
    kwargs: dict[str, Any] = {}
    if icc_profile:
        kwargs["icc_profile"] = bytes(icc_profile)
    if suffix in {".jpg", ".jpeg"}:
        exif = Image.Exif()
        if description:
            exif[270] = description
        exif[305] = "PS-Sezhao"
        if capture_date:
            exif[306] = capture_date
        kwargs.update(
            quality=min(100, max(1, int(jpeg_quality))),
            subsampling=0,
            optimize=True,
            exif=exif.tobytes(),
        )
    elif suffix == ".png":
        pnginfo = PngImagePlugin.PngInfo()
        for key, value in metadata_payload.items():
            pnginfo.add_text(key, value)
        kwargs.update(compress_level=4, pnginfo=pnginfo)
    pil_image.save(destination, **kwargs)
    return destination


def build_contact_sheet(
    entries: Sequence[ContactSheetEntry | tuple[np.ndarray, str]],
    settings: OutputSettings | Mapping[str, Any] | None,
) -> np.ndarray:
    config = settings if isinstance(settings, OutputSettings) else OutputSettings.from_dict(settings)
    config = config.sanitized()
    normalized = [
        entry if isinstance(entry, ContactSheetEntry) else ContactSheetEntry(entry[0], str(entry[1]))
        for entry in entries
    ]
    if not normalized:
        raise ValueError("接触印样中没有图片。")
    columns = min(config.contact_columns, len(normalized))
    rows = math.ceil(len(normalized) / columns)
    padding = max(8, config.contact_cell_size // 30)
    label_height = 28 if config.contact_labels else 0
    cell_width = config.contact_cell_size
    cell_height = config.contact_cell_size + label_height
    background = (28, 28, 28) if config.contact_background == "dark" else (245, 245, 245)
    foreground = (235, 235, 235) if config.contact_background == "dark" else (30, 30, 30)
    canvas = Image.new(
        "RGB",
        (columns * cell_width, rows * cell_height),
        background,
    )
    draw = ImageDraw.Draw(canvas)
    for index, entry in enumerate(normalized):
        row, column = divmod(index, columns)
        x0 = column * cell_width
        y0 = row * cell_height
        rgb = np.clip(np.asarray(entry.image, dtype=np.float32), 0.0, 1.0)
        data = np.round(rgb * 255.0).astype(np.uint8)
        image = Image.fromarray(data, mode="RGB")
        image.thumbnail(
            (cell_width - padding * 2, config.contact_cell_size - padding * 2),
            Image.Resampling.LANCZOS,
        )
        image_x = x0 + (cell_width - image.width) // 2
        image_y = y0 + (config.contact_cell_size - image.height) // 2
        canvas.paste(image, (image_x, image_y))
        if config.contact_labels:
            label = str(entry.label).strip()
            if len(label) > 48:
                label = label[:45] + "…"
            try:
                draw.text((x0 + padding, y0 + config.contact_cell_size + 5), label, fill=foreground)
            except UnicodeEncodeError:
                safe = label.encode("ascii", "replace").decode("ascii")
                draw.text((x0 + padding, y0 + config.contact_cell_size + 5), safe, fill=foreground)
    return np.asarray(canvas, dtype=np.uint8).astype(np.float32) / 255.0


def settings_for_contact_sheet(settings: OutputSettings) -> OutputSettings:
    return replace(
        settings.sanitized(),
        color_space="srgb",
        resize_mode="original",
        sharpen="off",
        format_label="JPEG",
    )


def _clean_metadata_text(value: Any, *, limit: int = 240) -> str:
    text = str(value or "").replace("\x00", " ").strip()
    return re.sub(r"\s+", " ", text)[:limit]


def _exif_datetime(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidates = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y:%m:%d %H:%M:%S")
    for pattern in candidates:
        try:
            parsed = datetime.strptime(text, pattern)
            return parsed.strftime("%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
    return ""

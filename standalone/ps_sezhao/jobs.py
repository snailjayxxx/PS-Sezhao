from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .engine import Analysis, Controls, analyze_image
from .io_utils import load_image, make_preview, save_image
from .processing import process_image_tiled
from .raw_io import RawDecodeSettings, prepare_save_output
from .workspace import clamp_crop, crop_array

ProgressCallback = Callable[[int, int, str], None]


def run_job(job_path: str | Path, progress: ProgressCallback | None = None) -> list[str]:
    job_file = Path(job_path)
    job = json.loads(job_file.read_text(encoding="utf-8"))
    items = job.get("items") or []
    if not items:
        raise ValueError("任务中没有可处理的图像。")

    settings = job.get("settings") or {}
    default_controls = Controls.from_dict(settings.get("controls"))
    default_analysis = settings.get("analysis")
    default_crop = clamp_crop(settings.get("crop"))
    default_raw = RawDecodeSettings.from_dict(settings.get("raw_decode"))
    output_paths: list[str] = []

    for index, item in enumerate(items, start=1):
        input_path = Path(item["input"])
        output_path = Path(item["output"])
        if progress:
            progress(index - 1, len(items), input_path.name)
        raw_settings = RawDecodeSettings.from_dict(item.get("raw_decode") or default_raw.to_dict())
        image, metadata = load_image(input_path, raw_settings=raw_settings)
        item_analysis = item.get("analysis", default_analysis)
        item_controls = item.get("controls")
        analysis_source = make_preview(image, 1800)
        analysis = Analysis.from_dict(item_analysis) if item_analysis else analyze_image(analysis_source)
        controls = Controls.from_dict(item_controls) if item_controls else default_controls
        crop = clamp_crop(item.get("crop", default_crop))
        source = crop_array(image, crop)
        result = process_image_tiled(source, analysis, controls)
        result = prepare_save_output(result, metadata)
        save_image(
            output_path,
            result,
            bit_depth=int(item.get("bit_depth", job.get("bit_depth", 16))),
            icc_profile=metadata.get("icc_profile"),
            jpeg_quality=int(job.get("jpeg_quality", 95)),
        )
        output_paths.append(str(output_path))
        if progress:
            progress(index, len(items), output_path.name)

    result_manifest = job.get("result_manifest")
    if result_manifest:
        manifest_path = Path(result_manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("\n".join(output_paths) + "\n", encoding="utf-8")
    return output_paths


def write_job(path: str | Path, payload: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination

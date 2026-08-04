from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .engine import Analysis, Controls, analyze_image, process_image
from .io_utils import load_image, save_image

ProgressCallback = Callable[[int, int, str], None]


def run_job(job_path: str | Path, progress: ProgressCallback | None = None) -> list[str]:
    job_file = Path(job_path)
    job = json.loads(job_file.read_text(encoding="utf-8"))
    items = job.get("items") or []
    if not items:
        raise ValueError("任务中没有可处理的图像。")

    settings = job.get("settings") or {}
    controls = Controls.from_dict(settings.get("controls"))
    saved_analysis = settings.get("analysis")
    output_paths: list[str] = []

    for index, item in enumerate(items, start=1):
        input_path = Path(item["input"])
        output_path = Path(item["output"])
        if progress:
            progress(index - 1, len(items), input_path.name)
        image, metadata = load_image(input_path)
        analysis = Analysis.from_dict(saved_analysis) if saved_analysis else analyze_image(image)
        result = process_image(image, analysis, controls)
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

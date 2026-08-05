from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..engine import Controls
from .geometry import GeometrySettings
from .output import OutputSettings


@dataclass(frozen=True)
class RollProjectSettings:
    roll_name: str = ""
    film_stock: str = ""
    camera: str = ""
    capture_date: str = ""
    note: str = ""
    frame_prefix: str = ""
    frame_start: int = 1
    frame_padding: int = 4

    def sanitized(self) -> "RollProjectSettings":
        try:
            frame_start = int(self.frame_start)
        except (TypeError, ValueError):
            frame_start = 1
        try:
            frame_padding = int(self.frame_padding)
        except (TypeError, ValueError):
            frame_padding = 4
        return RollProjectSettings(
            roll_name=_clean_text(self.roll_name, 160),
            film_stock=_clean_text(self.film_stock, 160),
            camera=_clean_text(self.camera, 160),
            capture_date=_clean_text(self.capture_date, 64),
            note=_clean_text(self.note, 1000),
            frame_prefix=_clean_text(self.frame_prefix, 40),
            frame_start=max(0, min(999999, frame_start)),
            frame_padding=max(1, min(8, frame_padding)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self.sanitized())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "RollProjectSettings":
        if not value:
            return cls()
        fields = cls.__dataclass_fields__
        payload = {key: value[key] for key in fields if key in value}
        return cls(**payload).sanitized()

    def frame_number(self, position: int) -> str:
        config = self.sanitized()
        number = config.frame_start + max(0, int(position))
        return f"{config.frame_prefix}{number:0{config.frame_padding}d}"


@dataclass(frozen=True)
class RollProjectProgress:
    total: int
    analyzed: int
    edited: int
    exported: int

    @property
    def pending(self) -> int:
        return max(0, self.total - self.exported)

    @property
    def percent(self) -> int:
        if self.total <= 0:
            return 0
        return round(self.exported * 100 / self.total)


def apply_project_defaults(
    output_settings: OutputSettings | Mapping[str, Any] | None,
    project_settings: RollProjectSettings | Mapping[str, Any] | None,
    *,
    frame_number: str,
    overwrite_common: bool = False,
) -> OutputSettings:
    output = (
        output_settings
        if isinstance(output_settings, OutputSettings)
        else OutputSettings.from_dict(output_settings)
    ).sanitized()
    project = (
        project_settings
        if isinstance(project_settings, RollProjectSettings)
        else RollProjectSettings.from_dict(project_settings)
    ).sanitized()

    def choose(current: str, shared: str) -> str:
        return shared if overwrite_common or not current else current

    return OutputSettings.from_dict(
        {
            **output.to_dict(),
            "roll_name": choose(output.roll_name, project.roll_name),
            "film_stock": choose(output.film_stock, project.film_stock),
            "camera": choose(output.camera, project.camera),
            "capture_date": choose(output.capture_date, project.capture_date),
            "note": choose(output.note, project.note),
            "frame_number": frame_number or output.frame_number,
        }
    )


def assign_project_output_settings(
    image_states: Sequence[Any],
    project_settings: RollProjectSettings | Mapping[str, Any] | None,
    *,
    overwrite_common: bool = False,
    renumber_all: bool = False,
) -> tuple[str, ...]:
    project = (
        project_settings
        if isinstance(project_settings, RollProjectSettings)
        else RollProjectSettings.from_dict(project_settings)
    ).sanitized()
    assigned: list[str] = []
    for position, item in enumerate(image_states):
        existing = OutputSettings.from_dict(getattr(item, "output_settings", None))
        frame = project.frame_number(position) if renumber_all or not existing.frame_number else existing.frame_number
        updated = apply_project_defaults(
            existing,
            project,
            frame_number=frame,
            overwrite_common=overwrite_common,
        )
        item.output_settings = updated.to_dict()
        assigned.append(updated.frame_number)
    return tuple(assigned)


def calculate_project_progress(
    image_states: Iterable[Any],
    exported_paths: Iterable[str | Path] = (),
) -> RollProjectProgress:
    items = list(image_states)
    exported = {
        str(Path(path).expanduser().resolve(strict=False)).casefold()
        for path in exported_paths
    }
    default_controls = Controls().sanitized().to_dict()
    analyzed = 0
    edited = 0
    exported_count = 0
    for item in items:
        analysis = getattr(item, "analysis", None)
        if analysis:
            analyzed += 1
        controls = Controls.from_dict(getattr(item, "controls", None)).sanitized().to_dict()
        crop = tuple(getattr(item, "crop", (0.0, 0.0, 1.0, 1.0)))
        rotation = int(getattr(item, "rotation", 0) or 0)
        geometry = GeometrySettings.from_dict(getattr(item, "geometry", None))
        if (
            analysis
            or controls != default_controls
            or crop != (0.0, 0.0, 1.0, 1.0)
            or rotation
            or not geometry.is_identity
        ):
            edited += 1
        key = str(Path(getattr(item, "path", "")).expanduser().resolve(strict=False)).casefold()
        if key in exported:
            exported_count += 1
    return RollProjectProgress(
        total=len(items),
        analyzed=analyzed,
        edited=edited,
        exported=exported_count,
    )


def _clean_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]

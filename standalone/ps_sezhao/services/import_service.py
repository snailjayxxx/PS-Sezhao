from __future__ import annotations

from pathlib import Path
from typing import Iterable


SUPPORTED_SUFFIXES = frozenset(
    {
        ".tif",
        ".tiff",
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".dng",
        ".cr2",
        ".cr3",
        ".nef",
        ".arw",
        ".raf",
        ".rw2",
        ".orf",
        ".pef",
        ".srw",
    }
)


def canonical_path(path: Path) -> str:
    try:
        return str(path.resolve(strict=False)).casefold()
    except OSError:
        return str(path.absolute()).casefold()


def discover_supported_paths(path: Path, *, recursive: bool = True) -> list[Path]:
    """Return supported files for one file or scanned folder."""

    try:
        if path.is_file():
            return [path] if path.suffix.lower() in SUPPORTED_SUFFIXES else []
        if not path.is_dir():
            return []

        iterator = path.rglob("*") if recursive else path.glob("*")
        files = [
            candidate
            for candidate in iterator
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
        ]
        return sorted(files, key=lambda candidate: str(candidate).casefold())
    except OSError:
        return []


def collect_supported_paths(
    paths: Iterable[Path],
    *,
    recursive: bool = True,
) -> list[Path]:
    """Expand files and folders, removing duplicates while preserving order."""

    collected: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        for candidate in discover_supported_paths(Path(path), recursive=recursive):
            key = canonical_path(candidate)
            if key in seen:
                continue
            seen.add(key)
            collected.append(candidate)
    return collected

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Type

from tkinter import messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - source mode can still use the buttons
    DND_FILES = None
    TkinterDnD = None


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


def _canonical_path(path: Path) -> str:
    try:
        return str(path.resolve(strict=False)).casefold()
    except OSError:
        return str(path.absolute()).casefold()


def discover_supported_paths(path: Path) -> list[Path]:
    """Return supported images for one file or folder, including RAW files."""

    try:
        if path.is_file():
            return [path] if path.suffix.lower() in SUPPORTED_SUFFIXES else []
        if not path.is_dir():
            return []

        files = [
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
        ]
        return sorted(files, key=lambda candidate: str(candidate).casefold())
    except OSError:
        return []


def collect_supported_paths(paths: Iterable[Path]) -> list[Path]:
    """Expand files/folders and remove duplicates while preserving order."""

    collected: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        for candidate in discover_supported_paths(Path(path)):
            key = _canonical_path(candidate)
            if key in seen:
                continue
            seen.add(key)
            collected.append(candidate)
    return collected


def install_drag_drop_root(app_module: Any) -> bool:
    """Use the TkDND-enabled root before app_module.main creates the window."""

    if TkinterDnD is None:
        return False
    app_module.tk.Tk = TkinterDnD.Tk
    return True


def apply_v055_import_drop_patch(app_class: Type[Any]) -> None:
    """Repair image/folder import and add Explorer/Finder drag-and-drop."""

    if getattr(app_class, "_v055_import_drop_applied", False):
        return

    # v0.5.4 exposed these implementations only under underscored names, while
    # the import path calls the public names. Install the public aliases
    # unconditionally so both button imports and drag/drop use the same methods.
    alias_pairs = (
        ("detected_base", "_detected_base"),
        ("direct_base_units", "_direct_base_units"),
        ("set_direct_base_units", "_set_direct_base_units"),
        ("item_key", "_item_key"),
        ("item_snapshot", "_item_snapshot"),
        ("history_for", "_history_for"),
        ("record_history", "_record_history"),
        ("restore_snapshot", "_restore_snapshot"),
        ("update_history_buttons", "_update_history_buttons"),
    )
    for public_name, internal_name in alias_pairs:
        internal = getattr(app_class, internal_name, None)
        if internal is not None:
            setattr(app_class, public_name, internal)

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._drag_drop_enabled = False
        self._install_drop_targets()

    def install_drop_targets(self: Any) -> None:
        if DND_FILES is None or not hasattr(self.root, "drop_target_register"):
            return

        targets: list[Any] = []
        for widget in (self.root, getattr(self, "canvas", None), getattr(self, "file_tree", None)):
            if widget is not None and all(widget is not current for current in targets):
                targets.append(widget)

        installed = False
        for widget in targets:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_external_drop)
                installed = True
            except Exception:
                continue

        self._drag_drop_enabled = installed
        if installed:
            self.status.set("可点击添加图像/文件夹，也可从资源管理器或 Finder 拖入。")

    def parse_drop_paths(self: Any, raw_data: str) -> list[Path]:
        try:
            values = self.root.tk.splitlist(raw_data)
        except Exception:
            values = (raw_data,)
        return [Path(str(value)) for value in values if str(value).strip()]

    def open_dropped_paths(self: Any, paths: Iterable[Path], folder_count: int = 0) -> int:
        files = collect_supported_paths(paths)
        existing = {
            _canonical_path(Path(item.path))
            for item in self.items
            if getattr(item, "path", None) is not None
        }
        new_files = [path for path in files if _canonical_path(path) not in existing]

        if not new_files:
            self.status.set("拖入内容中没有新的可添加图片或 RAW 文件。")
            return 0

        before = len(self.items)
        try:
            self.open_paths(new_files)
        except Exception as exc:
            self.status.set(f"添加图片失败：{exc}")
            messagebox.showerror("添加图片失败", str(exc), parent=self.root)
            return 0

        added = max(0, len(self.items) - before)
        source_text = f"（含 {folder_count} 个文件夹）" if folder_count else ""
        self.status.set(f"拖放完成：新增 {added} 张图片{source_text}。")
        return added

    def on_external_drop(self: Any, event: Any) -> str:
        dropped = self._parse_drop_paths(getattr(event, "data", ""))
        folder_count = 0
        for path in dropped:
            try:
                folder_count += int(path.is_dir())
            except OSError:
                continue

        if not collect_supported_paths(dropped):
            messagebox.showinfo(
                "没有可添加的图像",
                "拖入内容中没有找到支持的图片或 RAW 文件。",
                parent=self.root,
            )
            return "break"

        self._open_dropped_paths(dropped, folder_count)
        return "break"

    app_class._build_ui = build_ui
    app_class._install_drop_targets = install_drop_targets
    app_class._parse_drop_paths = parse_drop_paths
    app_class._open_dropped_paths = open_dropped_paths
    app_class._on_external_drop = on_external_drop
    app_class._v055_import_drop_applied = True

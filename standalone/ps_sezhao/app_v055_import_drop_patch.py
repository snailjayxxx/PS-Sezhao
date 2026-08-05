from __future__ import annotations

from pathlib import Path
from typing import Any, Type

from tkinter import messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - drag/drop remains optional in source mode
    DND_FILES = None
    TkinterDnD = None


SUPPORTED_SUFFIXES = {
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


def install_drag_drop_root(app_module: Any) -> bool:
    """Use the TkDND-enabled root before app_module.main creates the window."""

    if TkinterDnD is None:
        return False
    app_module.tk.Tk = TkinterDnD.Tk
    return True


def apply_v055_import_drop_patch(app_class: Type[Any]) -> None:
    """Repair v0.5.4 method aliases and add Explorer/Finder file dropping."""

    if getattr(app_class, "_v055_import_drop_applied", False):
        return

    # v0.5.4 registered these methods only with underscored names, while its
    # closures call the public names. The first call to controls_value() then
    # raises AttributeError before an imported image can be added to the list.
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
        if not hasattr(app_class, public_name) and hasattr(app_class, internal_name):
            setattr(app_class, public_name, getattr(app_class, internal_name))

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._drag_drop_enabled = False
        self._install_drop_targets()

    def install_drop_targets(self: Any) -> None:
        if DND_FILES is None or not hasattr(self.root, "drop_target_register"):
            return

        targets = [self.root]
        for name in ("canvas", "file_tree"):
            widget = getattr(self, name, None)
            if widget is not None:
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

    def discover_dropped_folder(self: Any, folder: Path) -> list[Path]:
        found: list[Path] = []
        try:
            for candidate in folder.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                    found.append(candidate)
        except OSError:
            return found
        return sorted(found, key=lambda path: str(path).lower())

    def on_external_drop(self: Any, event: Any) -> str:
        dropped = self._parse_drop_paths(getattr(event, "data", ""))
        files: list[Path] = []
        folder_count = 0

        for path in dropped:
            try:
                if path.is_dir():
                    folder_count += 1
                    files.extend(self._discover_dropped_folder(path))
                elif path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                    files.append(path)
            except OSError:
                continue

        unique: list[Path] = []
        seen: set[str] = set()
        for path in files:
            try:
                key = str(path.resolve())
            except OSError:
                key = str(path)
            if key not in seen:
                seen.add(key)
                unique.append(path)

        if not unique:
            messagebox.showinfo("没有可添加的图像", "拖入内容中没有找到支持的图片或 RAW 文件。")
            return "break"

        before = len(self.items)
        self.open_paths(unique)
        added = len(self.items) - before
        source_text = f"（含 {folder_count} 个文件夹）" if folder_count else ""
        self.status.set(f"拖放完成：新增 {added} 张图片{source_text}。")
        return "break"

    app_class._build_ui = build_ui
    app_class._install_drop_targets = install_drop_targets
    app_class._parse_drop_paths = parse_drop_paths
    app_class._discover_dropped_folder = discover_dropped_folder
    app_class._on_external_drop = on_external_drop
    app_class._v055_import_drop_applied = True

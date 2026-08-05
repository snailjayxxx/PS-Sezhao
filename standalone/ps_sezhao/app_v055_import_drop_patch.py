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
    ".nrw",
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
    # closures call the public names. The first imported photo therefore raised
    # AttributeError inside load_index() in windowed builds with no console.
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
    original_open_paths = app_class.open_paths

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._drag_drop_enabled = False
        self._install_drop_targets()

    def open_paths(self: Any, paths: list[Path], *, replace: bool = False) -> None:
        before = len(self.items)
        try:
            original_open_paths(self, paths, replace=replace)
        except Exception as error:
            self.status.set("添加图片失败。")
            messagebox.showerror(
                "添加图片失败",
                f"{error}\n\n请保留这段错误信息用于反馈。v0.5.5 之后导入异常不会再静默消失。",
            )
            return
        added = len(self.items) - before
        if added > 0:
            self.status.set(f"已添加 {added} 张图片。可继续添加或直接拖入更多文件。")
        elif paths:
            self.status.set("没有新增图片：文件可能已在列表中，或格式不受支持。")

    def install_drop_targets(self: Any) -> None:
        if DND_FILES is None or not hasattr(self.root, "drop_target_register"):
            self.status.set("点击“添加图像/添加文件夹”导入；当前运行环境未启用系统拖放。")
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
                widget.dnd_bind("<<DropEnter>>", self._on_external_drop_enter)
                widget.dnd_bind("<<DropLeave>>", self._on_external_drop_leave)
                widget.dnd_bind("<<Drop>>", self._on_external_drop)
                installed = True
            except Exception:
                continue

        self._drag_drop_enabled = installed
        if installed:
            self.status.set("可点击添加图像/文件夹，也可从资源管理器或 Finder 拖入。")
        else:
            self.status.set("点击“添加图像/添加文件夹”导入；系统拖放初始化失败。")

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

    def on_external_drop_enter(self: Any, _event: Any) -> str:
        self.status.set("松开鼠标即可添加图片或文件夹。")
        return "copy"

    def on_external_drop_leave(self: Any, _event: Any) -> str:
        self.status.set("拖放已取消。")
        return "copy"

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
            self.status.set("拖入内容没有可识别的图片。")
            return "break"

        before = len(self.items)
        self.open_paths(unique)
        added = len(self.items) - before
        source_text = f"（含 {folder_count} 个文件夹）" if folder_count else ""
        self.status.set(f"拖放完成：新增 {added} 张图片{source_text}。")
        return "break"

    app_class._build_ui = build_ui
    app_class.open_paths = open_paths
    app_class._install_drop_targets = install_drop_targets
    app_class._parse_drop_paths = parse_drop_paths
    app_class._discover_dropped_folder = discover_dropped_folder
    app_class._on_external_drop_enter = on_external_drop_enter
    app_class._on_external_drop_leave = on_external_drop_leave
    app_class._on_external_drop = on_external_drop
    app_class._v055_import_drop_applied = True

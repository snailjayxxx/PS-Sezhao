from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable, Type

from tkinter import messagebox

from .services.import_service import (
    SUPPORTED_SUFFIXES,
    canonical_path as _canonical_path,
    collect_supported_paths,
    discover_supported_paths,
)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - buttons remain available without DnD
    DND_FILES = None
    TkinterDnD = None


MACOS_DND_DISABLED_REASON = (
    "macOS 稳定版已停用 Finder 拖放，以避免 TkDND 与系统 Tk/Tcl 在窗口启动或退出时崩溃。"
)


def tkdnd_supported_on_platform(platform: str | None = None) -> bool:
    """Return whether the optional native TkDND runtime may be loaded.

    The bundled macOS TkDND library can register Tcl exit handlers that call
    back into Python after the interpreter starts shutting down. On current
    Apple Silicon/macOS builds this can abort the whole process in
    ``PyEval_RestoreThread``. File and folder buttons provide the same import
    functionality, so the stable macOS build deliberately never loads TkDND.
    """

    return (sys.platform if platform is None else platform) != "darwin"


def _load_tkdnd(root: Any) -> tuple[bool, str | None, str | None]:
    if not tkdnd_supported_on_platform():
        return False, MACOS_DND_DISABLED_REASON, None
    if TkinterDnD is None:
        return False, "tkinterdnd2 is not installed", None

    try:
        require = getattr(TkinterDnD, "require", None)
        if not callable(require):
            require = getattr(TkinterDnD, "_require", None)
        if not callable(require):
            raise RuntimeError("TkinterDnD does not expose a load function")
        version = str(require(root))
        return True, None, version
    except Exception as exc:  # TclError and RuntimeError are expected fallbacks
        return False, f"{type(exc).__name__}: {exc}", None


def build_safe_root_class(original_root_class: Any) -> Any:
    """Build a Tk root that has DnD methods but never requires DnD to start.

    Windows uses normal ``tk.Tk`` initialization first, then loads TkDND as an
    optional capability. macOS never calls this function from
    ``install_drag_drop_root`` and therefore never loads the native TkDND
    library into the process.
    """

    wrapper_class = (
        getattr(TkinterDnD, "DnDWrapper", None)
        if TkinterDnD is not None
        else None
    )
    bases = (
        (original_root_class, wrapper_class)
        if isinstance(wrapper_class, type)
        else (original_root_class,)
    )
    original_init = original_root_class.__init__

    def safe_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        available, error, version = _load_tkdnd(self)
        self._ps_sezhao_dnd_available = available
        self._ps_sezhao_dnd_error = error
        self._ps_sezhao_dnd_version = version

    return type(
        "PSSezhaoTk",
        bases,
        {
            "__init__": safe_init,
            "_ps_sezhao_safe_tk_class": True,
        },
    )


class _TkModuleProxy:
    """Override only app_module.tk.Tk without mutating tkinter globally."""

    _ps_sezhao_dnd_proxy = True

    def __init__(self, original_module: Any) -> None:
        self._original_module = original_module
        self.Tk = build_safe_root_class(original_module.Tk)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original_module, name)


def install_drag_drop_root(app_module: Any) -> bool:
    """Install optional drag/drop only on platforms where it is stable."""

    if not tkdnd_supported_on_platform():
        # Most importantly, do not call TkinterDnD.require() and do not replace
        # tkinter.Tk. Merely bundling tkinterdnd2 is harmless; loading its native
        # Tcl extension is what caused the macOS abort.
        return False

    current_tk = app_module.tk
    if getattr(current_tk, "_ps_sezhao_dnd_proxy", False):
        return TkinterDnD is not None

    app_module.tk = _TkModuleProxy(current_tk)
    return TkinterDnD is not None


def apply_v055_import_drop_patch(app_class: Type[Any]) -> None:
    """Repair image/folder import and add optional Explorer/Finder DnD."""

    if getattr(app_class, "_v055_import_drop_applied", False):
        return

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
        self._drag_drop_error = (
            MACOS_DND_DISABLED_REASON
            if not tkdnd_supported_on_platform()
            else getattr(self.root, "_ps_sezhao_dnd_error", None)
        )
        self._install_drop_targets()

    def install_drop_targets(self: Any) -> None:
        available = bool(getattr(self.root, "_ps_sezhao_dnd_available", False))
        if (
            DND_FILES is None
            or not available
            or not hasattr(self.root, "drop_target_register")
            or not hasattr(self.root, "dnd_bind")
        ):
            self._drag_drop_enabled = False
            self._drag_drop_error = (
                MACOS_DND_DISABLED_REASON
                if not tkdnd_supported_on_platform()
                else getattr(self.root, "_ps_sezhao_dnd_error", None)
            )
            if not tkdnd_supported_on_platform():
                self.status.set(
                    "macOS 稳定模式：请使用“添加图像”或“添加文件夹”；Finder 拖放已停用。"
                )
            else:
                self.status.set(
                    "拖放组件不可用；程序仍可正常使用“添加图像”和“添加文件夹”。"
                )
            return

        targets: list[Any] = []
        for widget in (
            self.root,
            getattr(self, "canvas", None),
            getattr(self, "file_tree", None),
        ):
            if widget is not None and all(widget is not current for current in targets):
                targets.append(widget)

        installed = False
        errors: list[str] = []
        for widget in targets:
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_external_drop)
                installed = True
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

        self._drag_drop_enabled = installed
        if installed:
            self.status.set("可点击添加图像/文件夹，也可从资源管理器拖入。")
        else:
            self._drag_drop_error = "; ".join(errors) or "无法注册拖放目标"
            self.status.set(
                "拖放组件加载后无法注册目标；请使用“添加图像”或“添加文件夹”。"
            )

    def parse_drop_paths(self: Any, raw_data: str) -> list[Path]:
        try:
            values = self.root.tk.splitlist(raw_data)
        except Exception:
            values = (raw_data,)
        return [Path(str(value)) for value in values if str(value).strip()]

    def open_dropped_paths(
        self: Any,
        paths: Iterable[Path],
        folder_count: int = 0,
    ) -> int:
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

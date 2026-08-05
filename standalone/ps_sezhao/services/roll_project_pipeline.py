from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Type

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..core.output import OutputSettings
from ..core.roll_project import (
    RollProjectSettings,
    apply_project_defaults,
    assign_project_output_settings,
    calculate_project_progress,
)
from ..storage.paths import default_project_database_path
from ..storage.project_store import normalized_file_path
from ..storage.roll_project_store import RollProjectStore, StoredRollProject


PRESET_METADATA_KEYS = {
    "roll_name",
    "film_stock",
    "camera",
    "capture_date",
    "frame_number",
    "note",
}


def apply_roll_project_pipeline(app_class: Type[Any]) -> None:
    """Add multi-roll projects, automatic frame numbering and output presets."""

    if getattr(app_class, "_roll_project_pipeline_applied", False):
        return

    original_init = app_class.__init__
    original_build_variables = app_class._build_variables
    original_build_file_panel = app_class._build_file_panel
    original_open_paths = app_class.open_paths
    original_save_project_session_now = app_class._save_project_session_now
    original_restore_project_session = app_class._restore_project_session
    original_handle_export_event = app_class._handle_export_event
    original_remove_selected = app_class.remove_selected
    original_clear_items = app_class.clear_items

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.active_roll_title = tk.StringVar(value="临时工作区")
        self.active_roll_summary = tk.StringVar(value="尚未创建胶卷项目")

    def init(
        self: Any,
        root: Any,
        *,
        lr_job: str | None = None,
        initial_files: list[str] | None = None,
    ) -> None:
        self.roll_project_store = RollProjectStore(default_project_database_path())
        try:
            pending_project_id = self.roll_project_store.get_active_project_id()
        except Exception:
            pending_project_id = None
        self._roll_restore_pending = bool(pending_project_id and lr_job is None and not initial_files)
        self._roll_project_loading = False
        self.active_roll_project_id: str | None = pending_project_id
        self.active_roll_project_name = ""
        self.active_roll_project_settings = RollProjectSettings()
        self.active_roll_output_preset_id: str | None = None
        self.roll_new_button: ttk.Button | None = None
        self.roll_open_button: ttk.Button | None = None
        self.roll_settings_button: ttk.Button | None = None
        self.output_presets_button: ttk.Button | None = None

        original_init(self, root, lr_job=lr_job, initial_files=initial_files)
        if self._roll_restore_pending:
            self._restore_active_roll_project()
        else:
            self._refresh_roll_project_status()

    def build_file_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_file_panel(self, parent)
        title = next(
            (
                child
                for child in parent.winfo_children()
                if isinstance(child, ttk.Label)
                and str(child.cget("text")) == "图片列表"
            ),
            None,
        )
        if title is not None:
            title.grid_remove()

        header = ttk.LabelFrame(parent, text="胶卷项目", padding=(7, 5))
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            textvariable=self.active_roll_title,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            header,
            textvariable=self.active_roll_summary,
            foreground="#666",
            wraplength=300,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 5))

        self.roll_new_button = ttk.Button(header, text="新建", command=self.open_new_roll_dialog)
        self.roll_open_button = ttk.Button(header, text="打开", command=self.open_roll_manager)
        self.roll_settings_button = ttk.Button(header, text="设置", command=self.open_roll_settings)
        self.output_presets_button = ttk.Button(header, text="输出预设", command=self.open_output_preset_manager)
        self.roll_new_button.grid(row=2, column=0, sticky="ew", padx=(0, 2))
        self.roll_open_button.grid(row=2, column=1, sticky="ew", padx=2)
        self.roll_settings_button.grid(row=2, column=2, sticky="ew", padx=2)
        self.output_presets_button.grid(row=2, column=3, sticky="ew", padx=(2, 0))
        for column in range(4):
            header.columnconfigure(column, weight=1)

    def open_paths(self: Any, paths: list[Path], *, replace: bool = False) -> None:
        original_open_paths(self, paths, replace=replace)
        if not self.active_roll_project_id or self._roll_project_loading:
            return
        assign_project_output_settings(
            self.items,
            self.active_roll_project_settings,
            overwrite_common=False,
            renumber_all=False,
        )
        item = self.current_item()
        if item is not None and hasattr(self, "_apply_output_settings_to_ui"):
            self._apply_output_settings_to_ui(item.output_settings)
        self._schedule_project_save()
        self._refresh_roll_project_status()

    def save_project_session_now(self: Any) -> None:
        original_save_project_session_now(self)
        self._save_active_roll_project()

    def restore_project_session(self: Any) -> None:
        if self._roll_restore_pending and self.active_roll_project_id:
            self._restore_active_roll_project()
            return
        original_restore_project_session(self)

    def remove_selected(self: Any) -> None:
        before = len(self.items)
        original_remove_selected(self)
        if len(self.items) != before:
            self._save_active_roll_project()
            self._refresh_roll_project_status()

    def clear_items(self: Any) -> None:
        before = len(self.items)
        original_clear_items(self)
        if before and not self.items:
            self._save_active_roll_project()
            self._refresh_roll_project_status()

    def handle_export_event(self: Any, event: Any) -> None:
        original_handle_export_event(self, event)
        if (
            event.kind == "item_succeeded"
            and self.active_roll_project_id
            and event.task is not None
        ):
            try:
                self.roll_project_store.mark_exported(
                    self.active_roll_project_id,
                    event.task.source,
                    event.task.destination,
                )
            except Exception:
                pass
            self._refresh_roll_project_status()

    def save_active_roll_project(self: Any) -> None:
        project_id = self.active_roll_project_id
        if not project_id or self._roll_project_loading or not self._project_persistence_enabled:
            return
        current = self.current_item()
        image_states = [_photo_state_payload(item) for item in self.items]
        try:
            self.roll_project_store.save_project(
                project_id=project_id,
                name=self.active_roll_project_name or "未命名胶卷",
                shared=self.active_roll_project_settings.to_dict(),
                image_states=image_states,
                file_paths=[item.path for item in self.items],
                current_file=None if current is None else current.path,
                output_preset_id=self.active_roll_output_preset_id,
            )
        except Exception as exc:
            self.status.set(f"保存胶卷项目失败：{exc}")
            return
        self._refresh_roll_project_status()

    def restore_active_roll_project(self: Any) -> None:
        project_id = self.active_roll_project_id
        if not project_id:
            return
        try:
            project = self.roll_project_store.load_project(project_id)
        except Exception as exc:
            self.status.set(f"读取胶卷项目失败：{exc}")
            return
        if project is None:
            self.active_roll_project_id = None
            self._roll_restore_pending = False
            try:
                self.roll_project_store.set_active_project(None)
            except Exception:
                pass
            original_restore_project_session(self)
            return
        self._load_roll_project(project)

    def load_roll_project(self: Any, project: StoredRollProject) -> None:
        paths = [Path(item.file_path) for item in project.items if Path(item.file_path).is_file()]
        self._roll_project_loading = True
        self._project_restoring = True
        try:
            self.active_roll_project_id = project.project_id
            self.active_roll_project_name = project.name
            self.active_roll_project_settings = RollProjectSettings.from_dict(project.shared)
            self.active_roll_output_preset_id = project.output_preset_id
            self.roll_project_store.set_active_project(project.project_id)
            self.open_paths(paths, replace=True)
            states = {normalized_file_path(item.file_path): item.state for item in project.items}
            for item in self.items:
                payload = states.get(normalized_file_path(item.path))
                if payload:
                    _restore_photo_state(item, payload)
                self._project_loaded_paths.add(normalized_file_path(item.path))
            assign_project_output_settings(
                self.items,
                self.active_roll_project_settings,
                overwrite_common=False,
                renumber_all=False,
            )
            target_index = 0
            if project.current_file:
                active = normalized_file_path(project.current_file)
                for index, item in enumerate(self.items):
                    if normalized_file_path(item.path) == active:
                        target_index = index
                        break
            if self.items:
                self.load_index(target_index)
            else:
                self._clear_current_display()
            self.status.set(f"已打开胶卷项目“{project.name}”，共 {len(self.items)} 张图片。")
        finally:
            self._project_restoring = False
            self._roll_project_loading = False
            self._roll_restore_pending = False
            self._refresh_roll_project_status()

    def activate_roll_project(self: Any, project_id: str) -> None:
        if self.active_roll_project_id:
            self._store_current_state()
            self._save_active_roll_project()
        project = self.roll_project_store.load_project(project_id)
        if project is None:
            messagebox.showerror("无法打开项目", "所选胶卷项目不存在或已经被删除。")
            return
        self._load_roll_project(project)

    def open_new_roll_dialog(self: Any) -> None:
        self._open_roll_settings_dialog(create_new=True)

    def open_roll_settings(self: Any) -> None:
        if not self.active_roll_project_id:
            self._open_roll_settings_dialog(create_new=True)
            return
        self._open_roll_settings_dialog(create_new=False)

    def open_roll_settings_dialog(self: Any, *, create_new: bool) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("新建胶卷项目" if create_new else "胶卷项目设置")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)
        current = RollProjectSettings() if create_new else self.active_roll_project_settings
        name_var = tk.StringVar(
            value=(current.roll_name or f"胶卷 {date.today().isoformat()}")
            if create_new
            else self.active_roll_project_name
        )
        roll_var = tk.StringVar(value=current.roll_name)
        film_var = tk.StringVar(value=current.film_stock)
        camera_var = tk.StringVar(value=current.camera)
        date_var = tk.StringVar(value=current.capture_date or date.today().isoformat())
        prefix_var = tk.StringVar(value=current.frame_prefix)
        start_var = tk.IntVar(value=current.frame_start)
        padding_var = tk.IntVar(value=current.frame_padding)
        note_var = tk.StringVar(value=current.note)
        include_current = tk.BooleanVar(value=True)
        apply_common = tk.BooleanVar(value=not create_new)
        renumber = tk.BooleanVar(value=create_new)

        labels = (
            ("项目名称", name_var),
            ("胶卷或批次名称", roll_var),
            ("胶卷型号", film_var),
            ("相机或扫描仪", camera_var),
            ("日期", date_var),
            ("画面编号前缀", prefix_var),
            ("起始编号", start_var),
            ("编号位数", padding_var),
            ("备注", note_var),
        )
        for row, (label, variable) in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            if variable is note_var:
                ttk.Entry(frame, textvariable=variable, width=42).grid(row=row, column=1, sticky="ew", pady=3)
            elif variable is start_var:
                ttk.Spinbox(frame, from_=0, to=999999, textvariable=variable, width=10).grid(row=row, column=1, sticky="w", pady=3)
            elif variable is padding_var:
                ttk.Spinbox(frame, from_=1, to=8, textvariable=variable, width=10).grid(row=row, column=1, sticky="w", pady=3)
            else:
                ttk.Entry(frame, textvariable=variable, width=42).grid(row=row, column=1, sticky="ew", pady=3)
        frame.columnconfigure(1, weight=1)
        options_row = len(labels)
        if create_new:
            ttk.Checkbutton(
                frame,
                text="将当前图片列表加入新项目",
                variable=include_current,
            ).grid(row=options_row, column=0, columnspan=2, sticky="w", pady=(8, 2))
            options_row += 1
        else:
            ttk.Checkbutton(
                frame,
                text="将公共信息覆盖到全部图片",
                variable=apply_common,
            ).grid(row=options_row, column=0, columnspan=2, sticky="w", pady=(8, 2))
            options_row += 1
        ttk.Checkbutton(
            frame,
            text="按照当前图片顺序重新生成画面编号",
            variable=renumber,
        ).grid(row=options_row, column=0, columnspan=2, sticky="w", pady=2)

        def commit() -> None:
            try:
                settings = RollProjectSettings(
                    roll_name=roll_var.get(),
                    film_stock=film_var.get(),
                    camera=camera_var.get(),
                    capture_date=date_var.get(),
                    note=note_var.get(),
                    frame_prefix=prefix_var.get(),
                    frame_start=start_var.get(),
                    frame_padding=padding_var.get(),
                ).sanitized()
                name = " ".join(name_var.get().split())
                if not name:
                    raise ValueError("项目名称不能为空。")
                if create_new:
                    if self.active_roll_project_id:
                        self._store_current_state()
                        self._save_active_roll_project()
                    project_id = self.roll_project_store.create_project(
                        name,
                        shared=settings.to_dict(),
                        make_active=True,
                    )
                    self.active_roll_project_id = project_id
                    self.active_roll_project_name = name
                    self.active_roll_project_settings = settings
                    self.active_roll_output_preset_id = None
                    if not include_current.get():
                        self.items.clear()
                        self.current_index = None
                        self.refresh_file_tree()
                        self._clear_current_display()
                else:
                    self.active_roll_project_name = name
                    self.active_roll_project_settings = settings
                assign_project_output_settings(
                    self.items,
                    settings,
                    overwrite_common=apply_common.get() if not create_new else True,
                    renumber_all=renumber.get(),
                )
                current_item = self.current_item()
                if current_item is not None and hasattr(self, "_apply_output_settings_to_ui"):
                    self._apply_output_settings_to_ui(current_item.output_settings)
                self._save_active_roll_project()
                self._refresh_roll_project_status()
            except Exception as exc:
                messagebox.showerror("无法保存胶卷项目", str(exc), parent=dialog)
                return
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=options_row + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="取消", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="保存", command=commit).pack(side="right")
        dialog.grab_set()
        dialog.wait_visibility()
        dialog.focus_set()

    def open_roll_manager(self: Any) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("打开胶卷项目")
        dialog.transient(self.root)
        dialog.geometry("650x390")
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(
            frame,
            columns=("name", "roll", "count", "exported", "updated"),
            show="headings",
            selectmode="browse",
        )
        headings = {
            "name": "项目",
            "roll": "胶卷/批次",
            "count": "图片",
            "exported": "已导出",
            "updated": "最后更新",
        }
        for key, label in headings.items():
            tree.heading(key, text=label)
        tree.column("name", width=170, stretch=True)
        tree.column("roll", width=150, stretch=True)
        tree.column("count", width=60, anchor="center", stretch=False)
        tree.column("exported", width=70, anchor="center", stretch=False)
        tree.column("updated", width=135, stretch=False)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        projects = self.roll_project_store.list_projects()
        for project in projects:
            shared = RollProjectSettings.from_dict(project.shared)
            updated = datetime.fromtimestamp(project.updated_at).strftime("%Y-%m-%d %H:%M")
            tree.insert(
                "",
                "end",
                iid=project.project_id,
                values=(project.name, shared.roll_name, project.item_count, project.exported_count, updated),
            )
        if self.active_roll_project_id and tree.exists(self.active_roll_project_id):
            tree.selection_set(self.active_roll_project_id)
            tree.focus(self.active_roll_project_id)

        def selected_id() -> str | None:
            focus = tree.focus()
            return focus or (tree.selection()[0] if tree.selection() else None)

        def open_selected() -> None:
            project_id = selected_id()
            if not project_id:
                return
            dialog.destroy()
            self._activate_roll_project(project_id)

        def delete_selected() -> None:
            project_id = selected_id()
            if not project_id:
                return
            values = tree.item(project_id, "values")
            name = values[0] if values else "所选项目"
            if not messagebox.askyesno("删除胶卷项目", f"删除“{name}”？原始图片不会被删除。", parent=dialog):
                return
            self.roll_project_store.delete_project(project_id)
            tree.delete(project_id)
            if self.active_roll_project_id == project_id:
                self.active_roll_project_id = None
                self.active_roll_project_name = ""
                self.active_roll_project_settings = RollProjectSettings()
                self.active_roll_output_preset_id = None
                self._refresh_roll_project_status()

        tree.bind("<Double-1>", lambda _event: open_selected())
        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="新建", command=lambda: (dialog.destroy(), self.open_new_roll_dialog())).pack(side="left")
        ttk.Button(buttons, text="删除", command=delete_selected).pack(side="left", padx=6)
        ttk.Button(buttons, text="关闭", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="打开", command=open_selected).pack(side="right", padx=(0, 6))
        dialog.grab_set()
        dialog.wait_visibility()
        dialog.focus_set()

    def open_output_preset_manager(self: Any) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("输出预设")
        dialog.transient(self.root)
        dialog.geometry("540x360")
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=("name", "format", "space", "size"), show="headings", selectmode="browse")
        for key, label in (("name", "名称"), ("format", "格式"), ("space", "色彩空间"), ("size", "尺寸")):
            tree.heading(key, text=label)
        tree.column("name", width=170, stretch=True)
        tree.column("format", width=110, stretch=False)
        tree.column("space", width=100, stretch=False)
        tree.column("size", width=110, stretch=False)
        tree.grid(row=0, column=0, sticky="nsew")
        preset_map: dict[str, Any] = {}

        def reload_tree() -> None:
            tree.delete(*tree.get_children())
            preset_map.clear()
            for preset in self.roll_project_store.list_output_presets():
                preset_map[preset.preset_id] = preset
                settings = OutputSettings.from_dict(preset.settings)
                size = settings.resize_mode if settings.resize_mode == "original" else f"{settings.resize_mode}:{settings.resize_value:g}"
                tree.insert(
                    "",
                    "end",
                    iid=preset.preset_id,
                    values=(preset.name, settings.format_name, settings.color_space, size),
                )

        def selected_preset() -> Any | None:
            focus = tree.focus()
            if not focus and tree.selection():
                focus = tree.selection()[0]
            return preset_map.get(focus)

        def save_current() -> None:
            name = simpledialog.askstring("保存输出预设", "预设名称：", parent=dialog)
            if not name:
                return
            settings = self._collect_output_settings().to_dict()
            payload = {key: value for key, value in settings.items() if key not in PRESET_METADATA_KEYS}
            try:
                preset_id = self.roll_project_store.save_output_preset(name, payload)
            except Exception as exc:
                messagebox.showerror("无法保存预设", str(exc), parent=dialog)
                return
            self.active_roll_output_preset_id = preset_id
            self._save_active_roll_project()
            reload_tree()
            tree.selection_set(preset_id)
            tree.focus(preset_id)

        def apply_preset(to_selected: bool) -> None:
            preset = selected_preset()
            if preset is None:
                return
            targets = self.selected_indices(default_all=False) if to_selected else ([self.current_index] if self.current_index is not None else [])
            if not targets:
                return
            technical = dict(preset.settings)
            for index in targets:
                if index is None or index < 0 or index >= len(self.items):
                    continue
                current = OutputSettings.from_dict(self.items[index].output_settings).to_dict()
                merged = {**current, **technical}
                self.items[index].output_settings = OutputSettings.from_dict(merged).to_dict()
            self.active_roll_output_preset_id = preset.preset_id
            current_item = self.current_item()
            if current_item is not None:
                self._apply_output_settings_to_ui(current_item.output_settings)
            self._schedule_project_save()
            self._save_active_roll_project()
            self.status.set(f"已应用输出预设“{preset.name}”到 {len(targets)} 张图片。")

        def delete_preset() -> None:
            preset = selected_preset()
            if preset is None:
                return
            if not messagebox.askyesno("删除输出预设", f"删除“{preset.name}”？", parent=dialog):
                return
            self.roll_project_store.delete_output_preset(preset.preset_id)
            if self.active_roll_output_preset_id == preset.preset_id:
                self.active_roll_output_preset_id = None
            reload_tree()

        reload_tree()
        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="保存当前设置", command=save_current).pack(side="left")
        ttk.Button(buttons, text="删除", command=delete_preset).pack(side="left", padx=6)
        ttk.Button(buttons, text="关闭", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="应用到选中", command=lambda: apply_preset(True)).pack(side="right", padx=(0, 6))
        ttk.Button(buttons, text="应用到当前", command=lambda: apply_preset(False)).pack(side="right", padx=(0, 6))
        dialog.grab_set()
        dialog.wait_visibility()
        dialog.focus_set()

    def refresh_roll_project_status(self: Any) -> None:
        if not self.active_roll_project_id:
            self.active_roll_title.set("临时工作区")
            self.active_roll_summary.set(f"当前 {len(self.items)} 张图片 · 未保存为胶卷项目")
            if self.roll_settings_button is not None:
                self.roll_settings_button.configure(text="设置")
            return
        exported_paths: tuple[str, ...] = ()
        try:
            stored = self.roll_project_store.load_project(self.active_roll_project_id)
            if stored is not None:
                exported_paths = stored.exported_paths
        except Exception:
            pass
        progress = calculate_project_progress(self.items, exported_paths)
        self.active_roll_title.set(f"{self.active_roll_project_name or '未命名胶卷'}")
        self.active_roll_summary.set(
            f"共 {progress.total} · 已分析 {progress.analyzed} · 已编辑 {progress.edited} · "
            f"已导出 {progress.exported}（{progress.percent}%）"
        )
        if self.roll_settings_button is not None:
            self.roll_settings_button.configure(text="设置")

    app_class._build_variables = build_variables
    app_class.__init__ = init
    app_class._build_file_panel = build_file_panel
    app_class.open_paths = open_paths
    app_class._save_project_session_now = save_project_session_now
    app_class._restore_project_session = restore_project_session
    app_class.remove_selected = remove_selected
    app_class.clear_items = clear_items
    app_class._handle_export_event = handle_export_event
    app_class._save_active_roll_project = save_active_roll_project
    app_class._restore_active_roll_project = restore_active_roll_project
    app_class._load_roll_project = load_roll_project
    app_class._activate_roll_project = activate_roll_project
    app_class.open_new_roll_dialog = open_new_roll_dialog
    app_class.open_roll_settings = open_roll_settings
    app_class._open_roll_settings_dialog = open_roll_settings_dialog
    app_class.open_roll_manager = open_roll_manager
    app_class.open_output_preset_manager = open_output_preset_manager
    app_class._refresh_roll_project_status = refresh_roll_project_status
    app_class._roll_project_pipeline_applied = True


def _photo_state_payload(item: Any) -> dict[str, Any]:
    return {
        "file_path": item.path,
        "controls": dict(getattr(item, "controls", {}) or {}),
        "analysis": None if getattr(item, "analysis", None) is None else dict(item.analysis),
        "crop": tuple(getattr(item, "crop", (0.0, 0.0, 1.0, 1.0))),
        "rotation": int(getattr(item, "rotation", 0) or 0),
        "geometry": dict(getattr(item, "geometry", {}) or {}),
        "raw_settings": dict(getattr(item, "raw_settings", {}) or {}),
        "output_settings": dict(getattr(item, "output_settings", {}) or {}),
    }


def _restore_photo_state(item: Any, payload: Mapping[str, Any]) -> None:
    item.controls = deepcopy(dict(payload.get("controls") or {}))
    item.analysis = None if payload.get("analysis") is None else deepcopy(dict(payload.get("analysis") or {}))
    crop = payload.get("crop") or (0.0, 0.0, 1.0, 1.0)
    item.crop = tuple(float(value) for value in crop)
    item.rotation = int(payload.get("rotation") or 0)
    item.geometry = deepcopy(dict(payload.get("geometry") or {}))
    item.raw_settings = deepcopy(dict(payload.get("raw_settings") or {}))
    item.output_settings = deepcopy(dict(payload.get("output_settings") or {}))
    item.__post_init__()

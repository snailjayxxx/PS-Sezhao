from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable, Type

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..storage.project_archive import (
    ARCHIVE_SUFFIX,
    ArchiveExportResult,
    ArchiveImportResult,
    ProjectIntegrityReport,
    RelinkResult,
    backup_project_database,
    check_project_integrity,
    export_project_archive,
    import_project_archive,
    inspect_project_archive,
    relink_project_sources,
    restore_project_database,
)


def apply_project_archive_pipeline(app_class: Type[Any]) -> None:
    """Add project archive, relink, integrity and database backup tools."""

    if getattr(app_class, "_project_archive_pipeline_applied", False):
        return

    original_init = app_class.__init__
    original_build_file_panel = app_class._build_file_panel

    def init(
        self: Any,
        root: Any,
        *,
        lr_job: str | None = None,
        initial_files: list[str] | None = None,
    ) -> None:
        self.project_tools_button: ttk.Button | None = None
        self._project_tool_busy = False
        original_init(self, root, lr_job=lr_job, initial_files=initial_files)

    def build_file_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_file_panel(self, parent)
        header = next(
            (
                child
                for child in parent.winfo_children()
                if isinstance(child, ttk.LabelFrame)
                and str(child.cget("text")) == "胶卷项目"
            ),
            None,
        )
        if header is None:
            return
        self.project_tools_button = ttk.Button(
            header,
            text="归档与迁移工具",
            command=self.open_project_archive_tools,
        )
        self.project_tools_button.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(5, 0),
        )

    def open_project_archive_tools(self: Any) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("胶卷项目归档与迁移")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="项目归档",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            frame,
            text="归档可只保存参数，也可连同原图一起打包。",
            foreground="#666",
            wraplength=430,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 8))

        buttons: list[ttk.Button] = []

        def add_button(row: int, text: str, command: Callable[[], None], description: str) -> None:
            button = ttk.Button(frame, text=text, width=19, command=command)
            button.grid(row=row, column=0, sticky="ew", padx=(0, 8), pady=3)
            ttk.Label(frame, text=description, foreground="#555", wraplength=280).grid(
                row=row,
                column=1,
                sticky="w",
                pady=3,
            )
            buttons.append(button)

        def set_busy(value: bool) -> None:
            self._project_tool_busy = value
            state = "disabled" if value else "normal"
            for button in buttons:
                button.configure(state=state)
            if self.project_tools_button is not None:
                self.project_tools_button.configure(state=state)

        def run_tool(
            status_text: str,
            worker: Callable[[], Any],
            success: Callable[[Any], None],
        ) -> None:
            if self._project_tool_busy:
                return
            set_busy(True)
            self.status.set(status_text)

            def execute() -> None:
                try:
                    result = worker()
                except Exception as exc:
                    self.root.after(0, lambda: finish_error(exc))
                    return
                self.root.after(0, lambda: finish_success(result))

            def finish_error(error: Exception) -> None:
                set_busy(False)
                self.status.set(f"项目工具执行失败：{error}")
                messagebox.showerror("项目工具失败", str(error), parent=dialog)

            def finish_success(result: Any) -> None:
                set_busy(False)
                success(result)

            threading.Thread(target=execute, daemon=True).start()

        def require_active_project() -> str | None:
            project_id = self.active_roll_project_id
            if not project_id:
                messagebox.showinfo("没有胶卷项目", "请先新建或打开一个胶卷项目。", parent=dialog)
                return None
            self._store_current_state()
            self._save_project_session_now()
            return project_id

        def export_current() -> None:
            project_id = require_active_project()
            if not project_id:
                return
            default_name = (self.active_roll_project_name or "胶卷项目") + ARCHIVE_SUFFIX
            destination = filedialog.asksaveasfilename(
                title="导出胶卷项目归档",
                parent=dialog,
                initialfile=default_name,
                defaultextension=ARCHIVE_SUFFIX,
                filetypes=[("PS-Sezhao 项目归档", f"*{ARCHIVE_SUFFIX}"), ("全部文件", "*.*")],
            )
            if not destination:
                return
            include_originals = messagebox.askyesno(
                "是否包含原图",
                "是否把所有仍可读取的原图一并写入归档？\n\n"
                "选择“否”时归档较小，但另一台电脑需要重新定位原图。",
                parent=dialog,
            )
            run_tool(
                "正在导出胶卷项目归档…",
                lambda: export_project_archive(
                    self.roll_project_store,
                    project_id,
                    destination,
                    include_originals=include_originals,
                ),
                lambda result: _show_export_result(self, dialog, result),
            )

        def import_archive() -> None:
            archive_path = filedialog.askopenfilename(
                title="导入胶卷项目归档",
                parent=dialog,
                filetypes=[("PS-Sezhao 项目归档", f"*{ARCHIVE_SUFFIX}"), ("全部文件", "*.*")],
            )
            if not archive_path:
                return
            try:
                inspection = inspect_project_archive(archive_path)
            except Exception as exc:
                messagebox.showerror("无法读取归档", str(exc), parent=dialog)
                return
            extract_to = None
            if inspection.contains_originals:
                extract_to = filedialog.askdirectory(
                    title="选择归档原图的解压目录",
                    parent=dialog,
                )
                if not extract_to:
                    return
            run_tool(
                "正在导入胶卷项目…",
                lambda: import_project_archive(
                    self.roll_project_store,
                    archive_path,
                    extract_originals_to=extract_to,
                    make_active=True,
                ),
                lambda result: _finish_import(self, dialog, result),
            )

        def relink_current() -> None:
            project_id = require_active_project()
            if not project_id:
                return
            root = filedialog.askdirectory(
                title="选择原图所在文件夹",
                parent=dialog,
            )
            if not root:
                return
            run_tool(
                "正在搜索并重新定位原图…",
                lambda: relink_project_sources(
                    self.roll_project_store,
                    project_id,
                    [root],
                    recursive=True,
                ),
                lambda result: _finish_relink(self, dialog, result),
            )

        def check_current() -> None:
            project_id = require_active_project()
            if not project_id:
                return
            verify_hashes = messagebox.askyesno(
                "深度完整性检查",
                "是否同时计算原图 SHA-256？\n\n"
                "深度检查更准确，但大尺寸 RAW 文件会需要较长时间。",
                parent=dialog,
            )
            run_tool(
                "正在检查胶卷项目完整性…",
                lambda: check_project_integrity(
                    self.roll_project_store,
                    project_id,
                    verify_hashes=verify_hashes,
                ),
                lambda result: _show_integrity_report(self, dialog, result),
            )

        def backup_database() -> None:
            destination = filedialog.asksaveasfilename(
                title="备份项目数据库",
                parent=dialog,
                initialfile="PS-Sezhao-workspace-backup.sqlite3",
                defaultextension=".sqlite3",
                filetypes=[("SQLite 数据库", "*.sqlite3"), ("全部文件", "*.*")],
            )
            if not destination:
                return
            self._store_current_state()
            self._save_project_session_now()
            run_tool(
                "正在备份项目数据库…",
                lambda: backup_project_database(self.roll_project_store, destination),
                lambda path: _finish_database_backup(self, dialog, path),
            )

        def restore_database() -> None:
            source = filedialog.askopenfilename(
                title="恢复项目数据库",
                parent=dialog,
                filetypes=[("SQLite 数据库", "*.sqlite3 *.db"), ("全部文件", "*.*")],
            )
            if not source:
                return
            if not messagebox.askyesno(
                "确认恢复数据库",
                "恢复会用所选备份替换当前项目数据库。\n"
                "当前数据库中的项目与输出预设将以备份内容为准。继续吗？",
                parent=dialog,
            ):
                return
            run_tool(
                "正在恢复项目数据库…",
                lambda: restore_project_database(self.roll_project_store, source),
                lambda _result: _finish_database_restore(self, dialog),
            )

        add_button(2, "导出当前项目", export_current, "生成可迁移的项目归档包")
        add_button(3, "导入项目归档", import_archive, "在本机创建独立的新胶卷项目")
        add_button(4, "重新定位原图", relink_current, "递归搜索移动后的同名原图")
        add_button(5, "检查项目完整性", check_current, "检查缺失、变化、编号和输出预设")
        add_button(6, "备份全部项目", backup_database, "在线备份完整 SQLite 数据库")
        add_button(7, "恢复全部项目", restore_database, "验证备份后替换当前数据库")
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)
        ttk.Separator(frame).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        ttk.Button(frame, text="关闭", command=dialog.destroy).grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="e",
        )
        dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: None if self._project_tool_busy else dialog.destroy(),
        )
        dialog.grab_set()
        dialog.wait_visibility()
        dialog.focus_set()

    app_class.__init__ = init
    app_class._build_file_panel = build_file_panel
    app_class.open_project_archive_tools = open_project_archive_tools
    app_class._project_archive_pipeline_applied = True


def _show_export_result(self: Any, parent: tk.Misc, result: ArchiveExportResult) -> None:
    self.status.set(f"项目归档已导出：{result.path.name}")
    messagebox.showinfo(
        "项目归档完成",
        f"归档：{result.path}\n"
        f"图片记录：{result.item_count}\n"
        f"已包含原图：{result.bundled_original_count}\n"
        f"缺失原图：{result.missing_original_count}\n"
        f"SHA-256：{result.sha256}",
        parent=parent,
    )


def _finish_import(self: Any, parent: tk.Misc, result: ArchiveImportResult) -> None:
    project = self.roll_project_store.load_project(result.project_id)
    if project is not None:
        self._load_roll_project(project)
    self.status.set(f"已导入胶卷项目“{result.project_name}”。")
    messagebox.showinfo(
        "项目导入完成",
        f"项目：{result.project_name}\n"
        f"图片记录：{result.item_count}\n"
        f"已解压原图：{result.extracted_original_count}\n"
        f"仍需重新定位：{result.missing_original_count}",
        parent=parent,
    )


def _finish_relink(self: Any, parent: tk.Misc, result: RelinkResult) -> None:
    project = self.roll_project_store.load_project(result.project_id)
    if project is not None:
        self._load_roll_project(project)
    self.status.set(f"已重新定位 {result.relinked_count} 张原图。")
    messagebox.showinfo(
        "原图重新定位完成",
        f"已重新定位：{result.relinked_count}\n"
        f"没有找到：{result.unresolved_count}\n"
        f"存在多个候选：{result.ambiguous_count}",
        parent=parent,
    )


def _show_integrity_report(
    self: Any,
    parent: tk.Misc,
    report: ProjectIntegrityReport,
) -> None:
    self.status.set("项目完整性检查通过。" if report.ok else "项目完整性检查发现需要处理的项目。")
    details = [
        f"项目：{report.project_name}",
        f"图片：{report.available}/{report.total} 可读取",
        f"缺失原图：{len(report.missing_paths)}",
        f"文件大小变化：{len(report.changed_paths)}",
        f"哈希不一致：{len(report.hash_mismatches)}",
        f"空画面编号：{len(report.empty_frame_numbers)}",
        f"重复画面编号：{len(report.duplicate_frame_numbers)}",
        f"输出预设缺失：{'是' if report.missing_output_preset else '否'}",
    ]
    problem_paths = (
        list(report.missing_paths)
        + list(report.changed_paths)
        + list(report.hash_mismatches)
        + list(report.duplicate_frame_numbers)
    )
    if problem_paths:
        details.append("\n前几项：")
        details.extend(f"- {Path(path).name}" for path in problem_paths[:8])
    show = messagebox.showinfo if report.ok else messagebox.showwarning
    show("项目完整性检查", "\n".join(details), parent=parent)


def _finish_database_backup(self: Any, parent: tk.Misc, path: Path) -> None:
    self.status.set(f"项目数据库已备份：{path.name}")
    messagebox.showinfo("数据库备份完成", f"备份已保存到：\n{path}", parent=parent)


def _finish_database_restore(self: Any, parent: tk.Misc) -> None:
    active_id = self.roll_project_store.get_active_project_id()
    if active_id:
        project = self.roll_project_store.load_project(active_id)
        if project is not None:
            self._load_roll_project(project)
    else:
        self.active_roll_project_id = None
        self.active_roll_project_name = ""
        self.active_roll_output_preset_id = None
        self.items.clear()
        self.current_index = None
        self.refresh_file_tree()
        self._clear_current_display()
        self._refresh_roll_project_status()
    self.status.set("项目数据库恢复完成。")
    messagebox.showinfo("数据库恢复完成", "项目、输出预设和活动状态已从备份恢复。", parent=parent)

from __future__ import annotations

from typing import Any, Type

import tkinter as tk
from tkinter import ttk


def _textvariable(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("textvariable"))
    except (AttributeError, tk.TclError):
        return ""


def apply_v073_style_status_patch(app_class: Type[Any]) -> None:
    """Use in-pane style selectors and move view state into the free top-right area."""

    if getattr(app_class, "_v073_style_status_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._v073_inline_style_lists: dict[str, dict[str, Any]] = {}
        self._v073_configure_style_selectors()
        self._v073_build_top_status_panel()

    def configure_style_selectors(self: Any) -> None:
        frame = getattr(self, "style_library_frame", None)
        scanner_box = getattr(self, "scanner_profile_box", None)
        film_box = getattr(self, "film_profile_box", None)
        if frame is None or scanner_box is None or film_box is None:
            return

        try:
            self.controls.columnconfigure(0, weight=1)
            frame.grid_configure(sticky="ew")
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=1)
        except tk.TclError:
            pass

        for child in frame.winfo_children():
            text = ""
            try:
                text = str(child.cget("text"))
            except (AttributeError, tk.TclError):
                pass
            if child in (scanner_box, film_box) or text in ("扫描仪风格", "胶卷风格"):
                child.grid_remove()

        self._v073_build_inline_selector(
            frame,
            kind="scanner",
            row=0,
            label="扫描仪风格",
            variable=self.scanner_profile_label,
            source_box=scanner_box,
        )
        self._v073_build_inline_selector(
            frame,
            kind="film",
            row=3,
            label="胶卷风格",
            variable=self.film_profile_label,
            source_box=film_box,
        )

    def build_inline_selector(
        self: Any,
        parent: ttk.LabelFrame,
        *,
        kind: str,
        row: int,
        label: str,
        variable: tk.StringVar,
        source_box: ttk.Combobox,
    ) -> None:
        block = ttk.Frame(parent)
        block.grid(row=row, column=0, columnspan=2, sticky="ew")
        block.columnconfigure(1, weight=1)

        ttk.Label(block, text=label).grid(row=0, column=0, sticky="w", padx=(0, 7))
        selector = ttk.Frame(block)
        selector.grid(row=0, column=1, sticky="ew")
        selector.columnconfigure(0, weight=1)

        entry = ttk.Entry(selector, textvariable=variable, state="readonly")
        entry.grid(row=0, column=0, sticky="ew")
        toggle = ttk.Button(
            selector,
            text="▼",
            width=3,
            command=lambda selected_kind=kind: self._v073_toggle_inline_style_list(selected_kind),
        )
        toggle.grid(row=0, column=1, padx=(3, 0))
        entry.bind(
            "<Button-1>",
            lambda _event, selected_kind=kind: self._v073_toggle_inline_style_list(selected_kind),
        )
        entry.bind(
            "<Return>",
            lambda _event, selected_kind=kind: self._v073_toggle_inline_style_list(selected_kind),
        )
        entry.bind(
            "<Down>",
            lambda _event, selected_kind=kind: self._v073_toggle_inline_style_list(selected_kind),
        )

        options = ttk.Frame(block, padding=(0, 3, 0, 2))
        options.grid(row=1, column=1, sticky="ew")
        options.columnconfigure(0, weight=1)
        options.grid_remove()

        listbox = tk.Listbox(
            options,
            activestyle="none",
            exportselection=False,
            height=8,
            borderwidth=1,
            highlightthickness=0,
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(options, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.grid(row=0, column=0, sticky="ew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.bind(
            "<ButtonRelease-1>",
            lambda _event, selected_kind=kind: self._v073_choose_inline_style(selected_kind),
        )
        listbox.bind(
            "<Return>",
            lambda _event, selected_kind=kind: self._v073_choose_inline_style(selected_kind),
        )
        listbox.bind("<Escape>", lambda _event: self._v073_close_inline_style_lists())

        self._v073_inline_style_lists[kind] = {
            "block": block,
            "entry": entry,
            "toggle": toggle,
            "options": options,
            "listbox": listbox,
            "source_box": source_box,
        }
        if kind == "scanner":
            self.scanner_style_selector = entry
            self.scanner_style_options = options
        else:
            self.film_style_selector = entry
            self.film_style_options = options

    def toggle_inline_style_list(self: Any, kind: str) -> str:
        item = self._v073_inline_style_lists.get(kind)
        if item is None:
            return "break"
        options = item["options"]
        was_open = bool(options.winfo_manager())
        self._v073_close_inline_style_lists()
        if was_open:
            return "break"

        if kind == "film":
            self._refresh_user_lut_library()
        source_box = item["source_box"]
        values = tuple(str(value) for value in source_box.cget("values"))
        listbox: tk.Listbox = item["listbox"]
        listbox.delete(0, "end")
        for value in values:
            listbox.insert("end", value)
        listbox.configure(height=max(1, min(12, len(values))))

        current = source_box.get()
        if current in values:
            index = values.index(current)
            listbox.selection_set(index)
            listbox.activate(index)
            listbox.see(index)

        options.grid()
        self.controls.update_idletasks()
        listbox.focus_set()
        return "break"

    def open_style_popup(self: Any, box: ttk.Combobox) -> str:
        """Compatibility entry point; no top-level popup is created."""

        pane_width = int(getattr(self, "style_library_frame").winfo_width())
        _ = pane_width
        kind = "film" if box is getattr(self, "film_profile_box", None) else "scanner"
        return self._v073_toggle_inline_style_list(kind)

    def choose_inline_style(self: Any, kind: str) -> str:
        item = self._v073_inline_style_lists.get(kind)
        if item is None:
            return "break"
        listbox: tk.Listbox = item["listbox"]
        selection = listbox.curselection()
        if selection:
            source_box: ttk.Combobox = item["source_box"]
            source_box.set(str(listbox.get(int(selection[0]))))
            source_box.event_generate("<<ComboboxSelected>>")
        self._v073_close_inline_style_lists()
        return "break"

    def close_inline_style_lists(self: Any) -> str:
        for item in self._v073_inline_style_lists.values():
            try:
                item["options"].grid_remove()
            except tk.TclError:
                pass
        return "break"

    def hide_local_status_labels(self: Any) -> None:
        for label in (
            getattr(self, "_v072_crop_status_label", None),
            getattr(self, "_v072_geometry_status_label", None),
        ):
            if label is not None:
                try:
                    label.grid_remove()
                except tk.TclError:
                    pass
        for group in getattr(self, "_v072_tool_groups", ()):
            for widget in group.winfo_children():
                if isinstance(widget, ttk.Label) and _textvariable(widget) == str(self.rotation_status):
                    try:
                        widget.grid_remove()
                    except tk.TclError:
                        pass

    def build_top_status_panel(self: Any) -> None:
        toolbar = next(
            (
                child
                for child in self.root.winfo_children()
                if isinstance(child, ttk.Frame)
                and str(child.grid_info().get("row")) == "0"
            ),
            None,
        )
        if toolbar is None:
            return

        for widget in toolbar.winfo_children():
            if isinstance(widget, ttk.Label) and _textvariable(widget) == str(self.status):
                widget.grid_remove()

        panel = ttk.LabelFrame(toolbar, text="当前状态", padding=(8, 4))
        panel.grid(row=0, column=9, rowspan=2, sticky="nsew", padx=(10, 3), pady=(0, 1))
        ttk.Label(panel, textvariable=self.status, anchor="e").grid(
            row=0, column=0, columnspan=3, sticky="ew"
        )
        ttk.Label(panel, textvariable=self.rotation_status, anchor="e").grid(
            row=1, column=0, sticky="e", padx=(0, 12), pady=(4, 0)
        )
        ttk.Label(panel, textvariable=self.crop_status, anchor="e").grid(
            row=1, column=1, sticky="e", padx=(0, 12), pady=(4, 0)
        )
        ttk.Label(panel, textvariable=self.geometry_status, anchor="e").grid(
            row=1, column=2, sticky="e", pady=(4, 0)
        )
        for column in range(3):
            panel.columnconfigure(column, weight=1)

        self._v073_top_status_panel = panel
        self._v073_hide_local_status_labels()

        viewbar = getattr(self, "_v072_viewbar", None)
        if viewbar is not None:
            viewbar.bind(
                "<Configure>",
                lambda _event: self.root.after_idle(self._v073_hide_local_status_labels),
                add="+",
            )
        geometry_bar = getattr(self, "_v072_geometry_bar", None)
        if geometry_bar is not None:
            geometry_bar.bind(
                "<Configure>",
                lambda _event: self.root.after_idle(self._v073_hide_local_status_labels),
                add="+",
            )
        self.root.after_idle(self._v073_hide_local_status_labels)

    app_class._build_ui = build_ui
    app_class._v073_configure_style_selectors = configure_style_selectors
    app_class._v073_build_inline_selector = build_inline_selector
    app_class._v073_toggle_inline_style_list = toggle_inline_style_list
    app_class._v073_open_style_popup = open_style_popup
    app_class._v073_choose_inline_style = choose_inline_style
    app_class._v073_close_inline_style_lists = close_inline_style_lists
    app_class._v073_hide_local_status_labels = hide_local_status_labels
    app_class._v073_build_top_status_panel = build_top_status_panel
    app_class._v073_style_status_applied = True

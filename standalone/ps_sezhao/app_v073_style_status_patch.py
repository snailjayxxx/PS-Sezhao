from __future__ import annotations

from typing import Any, Type

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


def _textvariable(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("textvariable"))
    except (AttributeError, tk.TclError):
        return ""


def apply_v073_style_status_patch(app_class: Type[Any]) -> None:
    """Use full-pane style popups and move view state into the free top-right area."""

    if getattr(app_class, "_v073_style_status_applied", False):
        return

    original_build_ui = app_class._build_ui

    def build_ui(self: Any) -> None:
        original_build_ui(self)
        self._v073_style_popup: tk.Toplevel | None = None
        self._v073_configure_style_selectors()
        self._v073_build_top_status_panel()

    def configure_style_selectors(self: Any) -> None:
        for box in (
            getattr(self, "scanner_profile_box", None),
            getattr(self, "film_profile_box", None),
        ):
            if box is None:
                continue
            box.configure(postcommand=lambda: None)
            box.bind(
                "<Button-1>",
                lambda _event, target=box: self._v073_open_style_popup(target),
                add=False,
            )
            box.bind(
                "<Return>",
                lambda _event, target=box: self._v073_open_style_popup(target),
                add=False,
            )
            box.bind(
                "<Down>",
                lambda _event, target=box: self._v073_open_style_popup(target),
                add=False,
            )

    def close_style_popup(self: Any) -> None:
        popup = getattr(self, "_v073_style_popup", None)
        self._v073_style_popup = None
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass

    def open_style_popup(self: Any, box: ttk.Combobox) -> str:
        self._v073_close_style_popup()
        if box is getattr(self, "film_profile_box", None):
            self._refresh_user_lut_library()

        values = tuple(str(value) for value in box.cget("values"))
        if not values:
            return "break"

        frame = getattr(self, "style_library_frame", None)
        if frame is None:
            return "break"

        self.root.update_idletasks()
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.transient(self.root)
        popup.configure(borderwidth=1, relief="solid")
        popup.attributes("-topmost", True)
        self._v073_style_popup = popup

        body = ttk.Frame(popup, padding=3)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        default_font = tkfont.nametofont("TkDefaultFont", root=self.root)
        visible_rows = min(14, len(values))
        listbox = tk.Listbox(
            body,
            activestyle="none",
            exportselection=False,
            font=default_font,
            height=visible_rows,
            borderwidth=0,
            highlightthickness=0,
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        for value in values:
            listbox.insert("end", value)
        current = box.get()
        if current in values:
            index = values.index(current)
            listbox.selection_set(index)
            listbox.activate(index)
            listbox.see(index)

        def choose(_event: tk.Event | None = None) -> str:
            selection = listbox.curselection()
            if selection:
                box.set(values[int(selection[0])])
                box.event_generate("<<ComboboxSelected>>")
            self._v073_close_style_popup()
            return "break"

        listbox.bind("<ButtonRelease-1>", choose)
        listbox.bind("<Return>", choose)
        listbox.bind("<Escape>", lambda _event: (self._v073_close_style_popup(), "break")[1])
        popup.bind("<Escape>", lambda _event: (self._v073_close_style_popup(), "break")[1])
        popup.bind("<FocusOut>", lambda _event: self.root.after(80, self._v073_close_style_popup))

        pane_left = int(frame.winfo_rootx())
        pane_width = max(280, int(frame.winfo_width()))
        root_left = int(self.root.winfo_rootx())
        root_right = root_left + int(self.root.winfo_width())
        pane_width = min(pane_width, max(280, root_right - pane_left - 8))

        popup.update_idletasks()
        requested_height = int(popup.winfo_reqheight())
        below_y = int(box.winfo_rooty() + box.winfo_height())
        root_bottom = int(self.root.winfo_rooty() + self.root.winfo_height())
        y = below_y
        if below_y + requested_height > root_bottom - 8:
            y = max(int(self.root.winfo_rooty()) + 8, int(box.winfo_rooty()) - requested_height)
        popup.geometry(f"{pane_width}x{requested_height}+{pane_left}+{y}")
        popup.lift()
        listbox.focus_set()
        return "break"

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
        panel.columnconfigure(0, weight=1)
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

        local_labels = (
            getattr(self, "_v072_crop_status_label", None),
            getattr(self, "_v072_geometry_status_label", None),
        )
        for label in local_labels:
            if label is not None:
                label.grid_remove()
        for group in getattr(self, "_v072_tool_groups", ()):
            for widget in group.winfo_children():
                if isinstance(widget, ttk.Label) and _textvariable(widget) == str(self.rotation_status):
                    widget.grid_remove()

        self._v073_top_status_panel = panel

    app_class._build_ui = build_ui
    app_class._v073_configure_style_selectors = configure_style_selectors
    app_class._v073_open_style_popup = open_style_popup
    app_class._v073_close_style_popup = close_style_popup
    app_class._v073_build_top_status_panel = build_top_status_panel
    app_class._v073_style_status_applied = True

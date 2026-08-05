from __future__ import annotations

from typing import Any, Iterator, Type

import tkinter as tk
from tkinter import ttk

from .engine import Controls
from .engine_style_v060_patch import (
    FILM_PROFILE_ORDER,
    FILM_PROFILES,
    SCANNER_PROFILE_ORDER,
    SCANNER_PROFILES,
    canonical_film_profile,
    canonical_scanner_profile,
)


def _walk_widgets(widget: tk.Misc) -> Iterator[tk.Misc]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def _label_to_key(profiles: dict[str, dict[str, Any]], order: tuple[str, ...]) -> dict[str, str]:
    return {str(profiles[key]["label"]): key for key in order}


FILM_LABEL_TO_KEY = _label_to_key(FILM_PROFILES, FILM_PROFILE_ORDER)
SCANNER_LABEL_TO_KEY = _label_to_key(SCANNER_PROFILES, SCANNER_PROFILE_ORDER)


def apply_v060_style_library_patch(app_class: Type[Any]) -> None:
    """Expose scanner and film styles as two independent per-photo controls."""

    if getattr(app_class, "_v060_style_library_applied", False):
        return

    original_build_variables = app_class._build_variables
    original_build_controls_panel = app_class._build_controls_panel
    original_controls_value = app_class.controls_value
    original_apply_controls = app_class.apply_controls

    def build_variables(self: Any) -> None:
        original_build_variables(self)
        self.scanner_profile = tk.StringVar(value="neutral_lab")
        self.scanner_profile_label = tk.StringVar(
            value=str(SCANNER_PROFILES["neutral_lab"]["label"])
        )
        self.film_profile_label = tk.StringVar(
            value=str(FILM_PROFILES["generic"]["label"])
        )
        self.scanner_strength = tk.DoubleVar(value=1.0)
        self.scanner_strength_text = tk.StringVar(value="100%")
        self.film_strength_text = tk.StringVar(value="100%")
        self.style_description = tk.StringVar(value="")

    def hide_legacy_style_widgets(self: Any) -> None:
        for child in self.controls.winfo_children():
            if isinstance(child, ttk.Combobox):
                try:
                    if str(child.cget("textvariable")) == str(self.profile):
                        child.grid_remove()
                except tk.TclError:
                    pass
                continue

            if isinstance(child, ttk.Label):
                try:
                    if str(child.cget("text")) == "胶片起始配置":
                        child.grid_remove()
                except tk.TclError:
                    pass
                continue

            if isinstance(child, ttk.Frame):
                for widget in _walk_widgets(child):
                    if not isinstance(widget, ttk.Label):
                        continue
                    try:
                        if str(widget.cget("text")) == "风格强度":
                            child.grid_remove()
                            break
                    except tk.TclError:
                        continue

    def add_strength_row(
        self: Any,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.DoubleVar,
        output: tk.StringVar,
        kind: str,
    ) -> None:
        line = ttk.Frame(parent)
        line.grid(row=row, column=0, sticky="ew", pady=(5, 0))
        line.columnconfigure(1, weight=1)
        ttk.Label(line, text=label, width=12).grid(row=0, column=0, sticky="w")
        scale = tk.Scale(
            line,
            from_=0.0,
            to=2.0,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            showvalue=False,
            highlightthickness=0,
            variable=variable,
            command=lambda _value, style_kind=kind: self._style_strength_changed(style_kind),
        )
        scale.grid(row=0, column=1, sticky="ew", padx=(4, 6))
        ttk.Label(line, textvariable=output, width=6, anchor="e").grid(row=0, column=2, sticky="e")

    def build_controls_panel(self: Any, parent: ttk.Frame) -> None:
        original_build_controls_panel(self, parent)
        self._hide_legacy_style_widgets()

        frame = ttk.LabelFrame(self.controls, text="扫描仪与胶卷风格 · v0.6.0", padding=7)
        frame.grid(row=0, column=0, sticky="ew", pady=(2, 10))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="扫描仪风格").grid(row=0, column=0, sticky="w", padx=(0, 5))
        scanner_box = ttk.Combobox(
            frame,
            textvariable=self.scanner_profile_label,
            values=tuple(str(SCANNER_PROFILES[key]["label"]) for key in SCANNER_PROFILE_ORDER),
            state="readonly",
            width=31,
        )
        scanner_box.grid(row=0, column=1, sticky="ew")
        scanner_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._style_selected("scanner"),
        )
        self._add_style_strength_row(
            frame,
            1,
            "扫描仪强度",
            self.scanner_strength,
            self.scanner_strength_text,
            "scanner",
        )

        ttk.Separator(frame, orient="horizontal").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(7, 7),
        )
        ttk.Label(frame, text="胶卷风格").grid(row=3, column=0, sticky="w", padx=(0, 5))
        film_box = ttk.Combobox(
            frame,
            textvariable=self.film_profile_label,
            values=tuple(str(FILM_PROFILES[key]["label"]) for key in FILM_PROFILE_ORDER),
            state="readonly",
            width=31,
        )
        film_box.grid(row=3, column=1, sticky="ew")
        film_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._style_selected("film"),
        )
        self._add_style_strength_row(
            frame,
            4,
            "胶卷强度",
            self.vars["style_strength"],
            self.film_strength_text,
            "film",
        )

        ttk.Label(
            frame,
            textvariable=self.style_description,
            foreground="#555",
            wraplength=295,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(7, 2))
        ttk.Label(
            frame,
            text="名称用于帮助识别常见观感；均为 PS-Sezhao 的非官方风格参考，并非厂商 ICC、DCP 或官方 LUT。",
            foreground="#777",
            wraplength=295,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self._update_style_library_text()

    def style_selected(self: Any, kind: str) -> None:
        if kind == "scanner":
            key = SCANNER_LABEL_TO_KEY.get(self.scanner_profile_label.get(), "neutral_lab")
            self.scanner_profile.set(key)
        else:
            key = FILM_LABEL_TO_KEY.get(self.film_profile_label.get(), "generic")
            self.profile.set(key)
        self._update_style_library_text()
        self._control_changed()

    def style_strength_changed(self: Any, _kind: str) -> None:
        self._update_style_library_text()
        self._control_changed()

    def update_style_library_text(self: Any) -> None:
        scanner_key = canonical_scanner_profile(self.scanner_profile.get())
        film_key = canonical_film_profile(self.profile.get())
        scanner_strength = float(self.scanner_strength.get())
        film_strength = float(self.vars["style_strength"].get())
        self.scanner_strength_text.set(f"{scanner_strength * 100:.0f}%")
        self.film_strength_text.set(f"{film_strength * 100:.0f}%")
        self.scanner_profile_label.set(str(SCANNER_PROFILES[scanner_key]["label"]))
        self.film_profile_label.set(str(FILM_PROFILES[film_key]["label"]))
        self.style_description.set(
            "扫描："
            + str(SCANNER_PROFILES[scanner_key]["description"])
            + "\n胶卷："
            + str(FILM_PROFILES[film_key]["description"])
        )

    def controls_value(self: Any) -> Controls:
        controls = original_controls_value(self)
        controls.profile = canonical_film_profile(self.profile.get())
        controls.scanner_profile = canonical_scanner_profile(self.scanner_profile.get())
        controls.scanner_strength = float(self.scanner_strength.get())
        return controls.sanitized()

    def apply_controls(self: Any, controls: Controls) -> None:
        controls = controls.sanitized()
        original_apply_controls(self, controls)
        self.profile.set(canonical_film_profile(controls.profile))
        self.scanner_profile.set(
            canonical_scanner_profile(getattr(controls, "scanner_profile", "neutral_lab"))
        )
        self.scanner_strength.set(float(getattr(controls, "scanner_strength", 1.0)))
        self._update_style_library_text()

    app_class._build_variables = build_variables
    app_class._build_controls_panel = build_controls_panel
    app_class._hide_legacy_style_widgets = hide_legacy_style_widgets
    app_class._add_style_strength_row = add_strength_row
    app_class._style_selected = style_selected
    app_class._style_strength_changed = style_strength_changed
    app_class._update_style_library_text = update_style_library_text
    app_class.controls_value = controls_value
    app_class.apply_controls = apply_controls
    app_class._v060_style_library_applied = True

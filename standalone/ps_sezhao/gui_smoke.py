from __future__ import annotations

import sys
from typing import Any, Sequence


GUI_SMOKE_FLAG = "--gui-smoke-test"
REQUIRE_DND_FLAG = "--require-dnd"


def requested_gui_smoke(argv: Sequence[str] | None = None) -> tuple[bool, bool]:
    values = list(sys.argv[1:] if argv is None else argv)
    return GUI_SMOKE_FLAG in values, REQUIRE_DND_FLAG in values


def run_gui_smoke(app_module: Any, *, require_dnd: bool = False) -> int:
    """Create the real configured window once, then close it immediately."""

    root = app_module.tk.Tk()
    root.withdraw()
    try:
        application = app_module.SezhaoApp(root)
        root.update_idletasks()

        required_widgets = (
            getattr(application, "file_tree", None),
            getattr(application, "canvas", None),
            getattr(application, "controls", None),
            getattr(application, "export_cancel_button", None),
            getattr(application, "sync_settings_button", None),
            getattr(application, "perspective_button", None),
            getattr(application, "output_settings_button", None),
            getattr(application, "contact_sheet_button", None),
            getattr(application, "roll_new_button", None),
            getattr(application, "roll_open_button", None),
            getattr(application, "roll_settings_button", None),
            getattr(application, "output_presets_button", None),
            getattr(application, "project_tools_button", None),
        )
        if any(widget is None or not bool(widget.winfo_exists()) for widget in required_widgets):
            raise RuntimeError("GUI smoke test could not create all core widgets")
        if getattr(application, "_output_service", None) is None:
            raise RuntimeError("GUI smoke test could not initialize the output queue")
        if getattr(application, "roll_project_store", None) is None:
            raise RuntimeError("GUI smoke test could not initialize roll project storage")
        if not hasattr(application, "open_project_archive_tools"):
            raise RuntimeError("GUI smoke test could not initialize project archive tools")
        if not hasattr(application, "straighten_angle") or not hasattr(application, "geometry_status"):
            raise RuntimeError("GUI smoke test could not create geometry controls")
        for attribute in (
            "output_color_space_label",
            "output_resize_mode_label",
            "output_filename_template",
            "output_collision_label",
            "output_film_stock",
            "contact_columns",
            "active_roll_title",
            "active_roll_summary",
        ):
            if not hasattr(application, attribute):
                raise RuntimeError(f"GUI smoke test could not create output/project setting: {attribute}")

        dnd_enabled = bool(getattr(root, "_ps_sezhao_dnd_available", False))
        dnd_error = getattr(root, "_ps_sezhao_dnd_error", None)
        print(
            "gui-smoke-test: ok "
            f"dnd={'enabled' if dnd_enabled else 'disabled'}"
            + (f" reason={dnd_error}" if dnd_error else "")
        )
        if require_dnd and not dnd_enabled:
            raise RuntimeError(
                "GUI opened, but the packaged TkDND runtime did not load: "
                f"{dnd_error or 'unknown reason'}"
            )
        return 0
    finally:
        root.destroy()

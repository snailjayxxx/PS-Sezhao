from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable


@dataclass(frozen=True)
class IntegrationStep:
    name: str
    apply: Callable[[], object]


@dataclass(frozen=True)
class BootstrapReport:
    configured_now: bool
    steps: tuple[str, ...]


_lock = RLock()
_configured = False


def integration_steps() -> tuple[IntegrationStep, ...]:
    """Return the ordered standalone integration plan."""

    from . import app as app_module
    from . import app_v052_source_crop_patch as source_crop_module
    from . import engine as engine_module
    from .app_v050_patch import apply_patch
    from .app_v051_raw_patch import apply_raw_patch
    from .app_v052_source_crop_patch import apply_source_crop_patch
    from .app_v053_scroll_patch import apply_scroll_patch
    from .app_v054_history_direct_patch import apply_v054_patch
    from .app_v054_sync_patch import apply_v054_sync_patch
    from .app_v055_import_drop_patch import (
        apply_v055_import_drop_patch,
        install_drag_drop_root,
    )
    from .app_v057_rotate_output_patch import apply_v057_rotate_output_patch
    from .app_v060_style_library_patch import apply_v060_style_library_patch
    from .app_v061_resizable_layout_patch import apply_v061_resizable_layout_patch
    from .engine_style_v060_patch import apply_style_engine_patch
    from .engine_v053_patch import apply_engine_patch
    from .services.project_session import apply_project_session
    from .services.runtime_service import install_runtime_bindings

    app_class = app_module.SezhaoApp

    return (
        IntegrationStep("engine.base", apply_engine_patch),
        IntegrationStep("engine.styles", apply_style_engine_patch),
        IntegrationStep(
            "runtime.bindings",
            lambda: install_runtime_bindings(
                app_module=app_module,
                source_crop_module=source_crop_module,
                engine_module=engine_module,
            ),
        ),
        IntegrationStep("ui.controls", lambda: apply_patch(app_class)),
        IntegrationStep("ui.raw", lambda: apply_raw_patch(app_class)),
        IntegrationStep("ui.crop", lambda: apply_source_crop_patch(app_class)),
        IntegrationStep("ui.scroll", lambda: apply_scroll_patch(app_class)),
        IntegrationStep("ui.history", lambda: apply_v054_patch(app_class)),
        IntegrationStep("ui.multi_image", lambda: apply_v054_sync_patch(app_class)),
        IntegrationStep("ui.import_drop", lambda: apply_v055_import_drop_patch(app_class)),
        IntegrationStep("ui.rotate_output", lambda: apply_v057_rotate_output_patch(app_class)),
        IntegrationStep("ui.styles", lambda: apply_v060_style_library_patch(app_class)),
        IntegrationStep("ui.resizable_layout", lambda: apply_v061_resizable_layout_patch(app_class)),
        IntegrationStep("storage.project_session", lambda: apply_project_session(app_class)),
        IntegrationStep("runtime.drag_drop_root", lambda: install_drag_drop_root(app_module)),
    )


def configure_application() -> BootstrapReport:
    """Configure the standalone application exactly once per process."""

    global _configured
    with _lock:
        steps = integration_steps()
        names = tuple(step.name for step in steps)
        if _configured:
            return BootstrapReport(configured_now=False, steps=names)

        for step in steps:
            step.apply()
        _configured = True
        return BootstrapReport(configured_now=True, steps=names)


def run_application(argv: list[str] | None = None) -> int:
    """Configure and run the desktop, batch or packaged GUI-test entry point."""

    configure_application()
    from . import app as app_module
    from .gui_smoke import requested_gui_smoke, run_gui_smoke

    smoke_requested, require_dnd = requested_gui_smoke(argv)
    if smoke_requested:
        return run_gui_smoke(app_module, require_dnd=require_dnd)
    return app_module.main(argv)

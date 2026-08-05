from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable

from .integration_groups import (
    build_context,
    install_drag_drop_group,
    install_engine_group,
    install_legacy_ui_group,
    install_persistence_service_group,
    install_processing_service_group,
    install_runtime_binding_group,
)


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
    """Return the small, ordered standalone integration plan."""

    from .services.lifecycle_facade import apply_lifecycle_facade

    context = build_context()
    return (
        IntegrationStep("engine.processing", lambda: install_engine_group(context)),
        IntegrationStep("runtime.bindings", lambda: install_runtime_binding_group(context)),
        IntegrationStep("ui.compatibility", lambda: install_legacy_ui_group(context)),
        IntegrationStep("services.processing", lambda: install_processing_service_group(context)),
        IntegrationStep("services.persistence", lambda: install_persistence_service_group(context)),
        IntegrationStep("lifecycle.facade", lambda: apply_lifecycle_facade(context.app_class)),
        IntegrationStep("runtime.drag_drop_root", lambda: install_drag_drop_group(context)),
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

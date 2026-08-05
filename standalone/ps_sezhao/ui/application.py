from __future__ import annotations

from typing import Any

from ..bootstrap import configure_application


def create_root() -> Any:
    """Create the configured Tk root used by the standalone application."""

    configure_application()
    from .. import app as app_module

    return app_module.tk.Tk()


def create_application(
    root: Any,
    *,
    lr_job: str | None = None,
    initial_files: list[str] | None = None,
) -> Any:
    """Build the configured standalone window without entering mainloop."""

    configure_application()
    from .. import app as app_module

    return app_module.SezhaoApp(root, lr_job=lr_job, initial_files=initial_files)

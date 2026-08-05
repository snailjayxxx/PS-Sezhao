from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

from . import __version__
from .storage.paths import (
    application_container,
    default_data_root,
    default_lut_directory,
    default_project_database_path,
    default_project_directory,
    default_startup_log_path,
    ensure_data_layout,
)


LOGGER_NAME = "ps_sezhao.startup"


def initialize_startup_environment() -> Path:
    """Create writable first-run folders and initialize persistent diagnostics."""

    ensure_data_layout()
    log_path = default_startup_log_path()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    if not any(
        isinstance(handler, RotatingFileHandler)
        and Path(getattr(handler, "baseFilename", "")) == log_path
        for handler in logger.handlers
    ):
        handler = RotatingFileHandler(
            log_path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        logger.addHandler(handler)

    logger.info("--- PS-Sezhao startup begin ---")
    logger.info("version=%s", __version__)
    logger.info("platform=%s", platform.platform())
    logger.info("python=%s", sys.version.replace("\n", " "))
    logger.info("executable=%s", sys.executable)
    logger.info("frozen=%s", bool(getattr(sys, "frozen", False)))
    logger.info("application_container=%s", application_container())
    logger.info("data_root=%s", default_data_root())
    logger.info("project_directory=%s", default_project_directory())
    logger.info("project_database=%s", default_project_database_path())
    logger.info("lut_directory=%s", default_lut_directory())
    _install_exception_hooks(logger, log_path)
    return log_path


def _install_exception_hooks(logger: logging.Logger, log_path: Path) -> None:
    def exception_hook(exc_type, exc_value, exc_traceback) -> None:
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        _show_startup_error(exc_value, log_path)

    sys.excepthook = exception_hook

    if hasattr(threading, "excepthook"):
        def thread_exception_hook(args) -> None:
            logger.error(
                "Unhandled thread exception in %s",
                getattr(args.thread, "name", "unknown"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = thread_exception_hook


def _show_startup_error(error: BaseException, log_path: Path) -> None:
    message = (
        "PS-Sezhao 无法启动。\n\n"
        f"错误：{type(error).__name__}: {error}\n\n"
        f"启动日志：{log_path}"
    )
    if sys.platform == "darwin":
        try:
            script = (
                'display alert "PS-Sezhao 无法启动" '
                f'message {message!r} as critical buttons {{"好"}} default button "好"'
            )
            subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return
        except Exception:
            pass
    try:
        from tkinter import messagebox

        messagebox.showerror("PS-Sezhao 无法启动", message)
    except Exception:
        pass


def run_guarded(application: Callable[..., int], argv: list[str] | None = None) -> int:
    """Run the packaged entrypoint and persist any pre-window failure."""

    log_path: Path | None = None
    try:
        log_path = initialize_startup_environment()
        result = application(argv)
        logging.getLogger(LOGGER_NAME).info(
            "application exited normally code=%s", result
        )
        return int(result or 0)
    except SystemExit:
        raise
    except BaseException as error:
        if log_path is None:
            try:
                log_path = default_startup_log_path()
            except Exception:
                log_path = Path.home() / "PS-Sezhao-startup.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write("\n--- fatal startup failure ---\n")
                stream.write("".join(traceback.format_exception(error)))
        except Exception:
            pass
        _show_startup_error(error, log_path)
        return 1

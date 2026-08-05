from __future__ import annotations

from typing import Any, Type

from ..storage.database_backup import (
    backup_project_database,
    restore_project_database,
)
from . import project_archive_pipeline


def apply_project_archive_platform_guard(app_class: Type[Any]) -> None:
    """Install database functions that close all handles before file replacement."""

    if getattr(app_class, "_project_archive_platform_guard_applied", False):
        return
    project_archive_pipeline.backup_project_database = backup_project_database
    project_archive_pipeline.restore_project_database = restore_project_database
    app_class._project_archive_platform_guard_applied = True

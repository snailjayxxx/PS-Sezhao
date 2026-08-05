from __future__ import annotations

import os
import sys
from pathlib import Path


ENV_PROJECT_DATABASE = "PS_SEZHAO_PROJECT_DB"


def default_project_database_path() -> Path:
    """Return the per-user recoverable workspace database path."""

    override = os.environ.get(ENV_PROJECT_DATABASE)
    if override:
        return Path(override).expanduser()

    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    elif os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
    else:
        state_home = os.environ.get("XDG_STATE_HOME")
        base = Path(state_home) if state_home else home / ".local" / "state"
    return base / "PS-Sezhao" / "workspace.sqlite3"

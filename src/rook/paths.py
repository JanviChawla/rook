import os
import sys
from pathlib import Path

from rook import branding

DATABASE_FILENAME = "data.sqlite3"


def default_data_directory() -> Path:
    """The per-user directory Rook's database lives in (Section 15.3, 20.10).

    Never the source repository, the current working directory, or the
    installed package directory.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Local")
        return Path(base) / branding.DISPLAY_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / branding.DISPLAY_NAME

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base_dir / branding.CONSOLE_COMMAND


def default_database_path() -> Path:
    return default_data_directory() / DATABASE_FILENAME

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    """Open a Rook database connection with the required pragmas (Section 15.4).

    Creates the parent directory if needed - the database must never be
    expected to already exist at a fresh install.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA busy_timeout = 3000;")
    connection.execute("PRAGMA journal_mode = DELETE;")
    connection.execute("PRAGMA synchronous = FULL;")
    return connection

import sqlite3

# Section 15.28: all four version-1 tables are created together in one
# migration, since Routines/Routine Items are part of the same accepted
# schema even though they remain unused until Phase 11.
CURRENT_SCHEMA_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE tasks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    text              TEXT NOT NULL CHECK (length(trim(text)) > 0),
    state             TEXT NOT NULL
                              CHECK (state IN ('open', 'migrated', 'completed', 'deleted')),
    sort_order        INTEGER NOT NULL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    state_changed_at  TEXT NOT NULL,
    state_date        TEXT NOT NULL,
    archived_date     TEXT,
    archived_at       TEXT,
    archive_order     INTEGER,

    CHECK (
        (archived_date IS NULL AND archived_at IS NULL AND archive_order IS NULL)
        OR
        (archived_date IS NOT NULL AND archived_at IS NOT NULL AND archive_order IS NOT NULL)
    ),

    CHECK (
        archived_date IS NULL
        OR state IN ('completed', 'deleted')
    )
);

CREATE TABLE routines (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL CHECK (length(trim(name)) > 0),
    sort_order  INTEGER NOT NULL,
    is_deleted  INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE routine_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id  INTEGER NOT NULL,
    text        TEXT NOT NULL CHECK (length(trim(text)) > 0),
    sort_order  INTEGER NOT NULL,
    is_deleted  INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,

    FOREIGN KEY (routine_id)
        REFERENCES routines(id)
        ON DELETE CASCADE
);

CREATE INDEX ix_tasks_active_order
ON tasks(archived_date, sort_order, id);

CREATE INDEX ix_tasks_archive_date_order
ON tasks(archived_date, archive_order, id);

CREATE INDEX ix_tasks_rollover
ON tasks(archived_date, state, state_date);

CREATE INDEX ix_routines_order
ON routines(sort_order, id);

CREATE INDEX ix_routine_items_order
ON routine_items(routine_id, is_deleted, sort_order, id);

CREATE UNIQUE INDEX ux_routines_active_name
ON routines(lower(trim(name)))
WHERE is_deleted = 0;
"""


class UnsupportedSchemaVersionError(RuntimeError):
    """Raised when the database's schema is newer than this build understands."""

    def __init__(self, found_version: int) -> None:
        super().__init__(
            f"This database uses schema version {found_version}, but this version "
            f"of Rook only understands up to version {CURRENT_SCHEMA_VERSION}. "
            "The database was left untouched."
        )
        self.found_version = found_version


def migrate(connection: sqlite3.Connection) -> None:
    """Bring the database up to CURRENT_SCHEMA_VERSION (Section 15.5).

    Safe to call every startup: a database already at the current version
    is left untouched. A database from a newer, not-yet-understood version
    is rejected rather than silently used or altered.
    """
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]

    if current_version > CURRENT_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(current_version)

    if current_version == 0:
        connection.executescript(_SCHEMA_V1)
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION};")
        connection.commit()

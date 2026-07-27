import pytest

from rook.persistence.database import connect
from rook.persistence.migrations import (
    CURRENT_SCHEMA_VERSION,
    UnsupportedSchemaVersionError,
    migrate,
)


def test_fresh_database_creates_schema_and_sets_version(tmp_path) -> None:
    connection = connect(tmp_path / "test.sqlite3")
    migrate(connection)

    version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == CURRENT_SCHEMA_VERSION

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert {"app_meta", "tasks", "routines", "routine_items"} <= tables


def test_migrate_is_a_no_op_on_an_already_current_database(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    connection = connect(path)
    migrate(connection)
    connection.execute(
        """
        INSERT INTO tasks (
            text, state, sort_order, created_at, updated_at, state_changed_at, state_date
        ) VALUES ('Existing', 'open', 1, 'x', 'x', 'x', 'x')
        """
    )
    connection.commit()

    migrate(connection)  # must not error or wipe existing data

    count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 1


def test_unsupported_future_schema_version_is_rejected(tmp_path) -> None:
    connection = connect(tmp_path / "test.sqlite3")
    connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1};")
    connection.commit()

    with pytest.raises(UnsupportedSchemaVersionError):
        migrate(connection)

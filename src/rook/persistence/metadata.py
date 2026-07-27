import sqlite3
from datetime import date

_LAST_PROCESSED_DATE_KEY = "last_processed_date"


class MetadataRepository:
    """SQL access for the small `app_meta` key/value table (Section 15.7)."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_last_processed_date(self) -> date | None:
        row = self._connection.execute(
            "SELECT value FROM app_meta WHERE key = ?", (_LAST_PROCESSED_DATE_KEY,)
        ).fetchone()
        return date.fromisoformat(row["value"]) if row is not None else None

    def set_last_processed_date(self, value: date) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO app_meta (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (_LAST_PROCESSED_DATE_KEY, value.isoformat()),
            )

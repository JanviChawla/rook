import sqlite3
from datetime import date

_LAST_PROCESSED_DATE_KEY = "last_processed_date"
_WEEK_START_DAY_KEY = "week_start_day"

# Python weekday() values: 0 = Monday, 6 = Sunday.
_WEEK_START_VALUES = {"sunday": 6, "monday": 0}
_WEEK_START_DEFAULT = 6  # Sunday


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

    def get_week_start_day(self) -> int:
        """Return the first weekday as a Python weekday() int (0=Mon, 6=Sun).

        Defaults to 6 (Sunday) when the key is absent or unrecognised.
        """
        row = self._connection.execute(
            "SELECT value FROM app_meta WHERE key = ?", (_WEEK_START_DAY_KEY,)
        ).fetchone()
        if row is None:
            return _WEEK_START_DEFAULT
        return _WEEK_START_VALUES.get(row["value"], _WEEK_START_DEFAULT)

    def set_week_start_day(self, first_weekday: int) -> None:
        """Persist week_start_day. first_weekday must be 0 (Mon) or 6 (Sun)."""
        label = next(k for k, v in _WEEK_START_VALUES.items() if v == first_weekday)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO app_meta (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (_WEEK_START_DAY_KEY, label),
            )

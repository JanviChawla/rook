import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

from rook.domain.tasks import TaskState


@dataclass(frozen=True, slots=True)
class ArchivedTask:
    text: str
    state: TaskState  # completed or deleted


class ArchiveRepository:
    """Read-only SQL access for the Archive (Section 21.14)."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_archive_dates(self) -> list[date]:
        """All distinct dates with archived tasks, newest first.

        Routine activity never sets archived_date on the tasks table, so
        the query naturally excludes it (FR-068).
        """
        rows = self._connection.execute(
            """
            SELECT DISTINCT archived_date
            FROM tasks
            WHERE archived_date IS NOT NULL
            ORDER BY archived_date DESC
            """
        ).fetchall()
        return [date.fromisoformat(row["archived_date"]) for row in rows]

    def list_week_items(
        self, week_start: date, week_end_exclusive: date
    ) -> list[tuple[date, list[ArchivedTask]]]:
        """Archived tasks in [week_start, week_end_exclusive), grouped by day.

        Days are returned oldest-first. Tasks within each day follow their
        original archive_order. Only completed and deleted tasks appear
        (the schema constraint ensures no open/migrated tasks are archived).
        """
        rows = self._connection.execute(
            """
            SELECT text, state, archived_date
            FROM tasks
            WHERE archived_date IS NOT NULL
              AND archived_date >= ?
              AND archived_date < ?
            ORDER BY archived_date ASC, archive_order ASC
            """,
            (week_start.isoformat(), week_end_exclusive.isoformat()),
        ).fetchall()

        grouped: dict[date, list[ArchivedTask]] = {}
        for row in rows:
            d = date.fromisoformat(row["archived_date"])
            grouped.setdefault(d, []).append(
                ArchivedTask(text=row["text"], state=TaskState(row["state"]))
            )
        return [(d, tasks) for d, tasks in grouped.items()]


def week_start_for(d: date, *, first_weekday: int) -> date:
    """Return the start of the calendar week containing d.

    first_weekday uses Python's weekday() convention: 0=Monday, 6=Sunday.
    """
    days_back = (d.weekday() - first_weekday) % 7
    return d - timedelta(days=days_back)

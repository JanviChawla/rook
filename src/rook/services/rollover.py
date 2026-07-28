import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from rook.persistence.metadata import MetadataRepository


@dataclass(frozen=True, slots=True)
class RolloverResult:
    """Summary sufficient for the screen to decide whether to refresh
    (Section 16.17)."""

    changed: bool


class RolloverService:
    """Owns Day Rollover (Section 5.2, 15.12, 16.17).

    Unlike ordinary Task mutations, archiving, renumbering, and updating
    `last_processed_date` must commit as a single atomic transaction, so
    this service holds the raw connection directly rather than composing
    calls to TaskRepository/MetadataRepository, each of which would commit
    independently and break that guarantee.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        metadata_repository: MetadataRepository,
        *,
        today_provider: Callable[[], date] = date.today,
        now_provider: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._connection = connection
        self._metadata = metadata_repository
        self._today_provider = today_provider
        self._now_provider = now_provider

    def roll_forward_if_needed(self) -> RolloverResult:
        today = self._today_provider()
        last_processed = self._metadata.get_last_processed_date()

        if last_processed is None:
            # First launch ever: nothing exists to archive yet.
            self._metadata.set_last_processed_date(today)
            return RolloverResult(changed=False)

        # Section 18.14: only roll forward, never backward. This single
        # comparison also handles multiple missed days (Section 18.13)
        # without any per-day loop - archive eligibility below is judged
        # against each Task's own state_date, not against "yesterday".
        if today <= last_processed:
            return RolloverResult(changed=False)

        timestamp = self._now_provider().isoformat()
        today_iso = today.isoformat()
        with self._connection:
            self._connection.execute(
                """
                UPDATE tasks
                SET archived_date = state_date, archived_at = ?, archive_order = sort_order
                WHERE archived_date IS NULL
                  AND state IN ('completed', 'deleted')
                  AND state_date < ?
                """,
                (timestamp, today_iso),
            )

            # Tasks marked Migrated on a previous day carry forward as Open
            # tasks today — the migration was an intent recorded yesterday,
            # and the new day is when that intent becomes an active task again.
            self._connection.execute(
                """
                UPDATE tasks
                SET state = 'open', state_date = ?, state_changed_at = ?, updated_at = ?
                WHERE archived_date IS NULL
                  AND state = 'migrated'
                  AND state_date < ?
                """,
                (today_iso, timestamp, timestamp, today_iso),
            )

            # Section 15.12 step 3: renumber remaining active Tasks so
            # sort_order stays contiguous, preserving relative order.
            remaining_ids = [
                row["id"]
                for row in self._connection.execute(
                    """
                    SELECT id FROM tasks
                    WHERE archived_date IS NULL
                    ORDER BY sort_order ASC, id ASC
                    """
                ).fetchall()
            ]
            for new_order, task_id in enumerate(remaining_ids, start=1):
                self._connection.execute(
                    "UPDATE tasks SET sort_order = ? WHERE id = ?", (new_order, task_id)
                )

            self._connection.execute(
                """
                INSERT INTO app_meta (key, value) VALUES ('last_processed_date', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (today_iso,),
            )

        return RolloverResult(changed=True)

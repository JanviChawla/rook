import sqlite3
from datetime import date, datetime

from rook.domain.tasks import Task, TaskState


class TaskRepository:
    """SQL access for active Tasks (Section 15.22). No Textual imports."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_active_tasks(self) -> list[Task]:
        rows = self._connection.execute(
            """
            SELECT id, text, state
            FROM tasks
            WHERE archived_date IS NULL
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
        return [_row_to_task(row) for row in rows]

    def create_task(self, text: str, *, now: datetime, local_date: date) -> Task:
        timestamp = now.isoformat()
        with self._connection:
            next_order = self._connection.execute(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM tasks WHERE archived_date IS NULL"
            ).fetchone()[0]
            cursor = self._connection.execute(
                """
                INSERT INTO tasks (
                    text, state, sort_order, created_at, updated_at,
                    state_changed_at, state_date
                ) VALUES (?, 'open', ?, ?, ?, ?, ?)
                """,
                (text, next_order, timestamp, timestamp, timestamp, local_date.isoformat()),
            )
            task_id = cursor.lastrowid
            assert task_id is not None, "INSERT must assign a row id"
        return Task(id=task_id, text=text, state=TaskState.OPEN)

    def update_task_text(self, task_id: int, text: str, *, now: datetime) -> Task:
        timestamp = now.isoformat()
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET text = ?, updated_at = ?
                WHERE id = ? AND archived_date IS NULL
                """,
                (text, timestamp, task_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"No active task with id {task_id}")
            row = self._connection.execute(
                "SELECT id, text, state FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return _row_to_task(row)

    def set_task_state(
        self, task_id: int, state: TaskState, *, now: datetime, local_date: date
    ) -> Task:
        """Section 15.9: state_date is stamped at the moment of the
        transition, not derived later, so historical Archive dates stay
        stable even if the user's time zone changes afterward."""
        timestamp = now.isoformat()
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE tasks
                SET state = ?, updated_at = ?, state_changed_at = ?, state_date = ?
                WHERE id = ? AND archived_date IS NULL
                """,
                (state.value, timestamp, timestamp, local_date.isoformat(), task_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"No active task with id {task_id}")
            row = self._connection.execute(
                "SELECT id, text, state FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return _row_to_task(row)

    def delete_active_task(self, task_id: int) -> Task:
        """Second-stage delete (Section 15.14): permanently remove a
        Soft-Deleted Task. Returns the row as it existed immediately
        before removal, so a future undo (Phase 7) has what it needs to
        restore it.
        """
        with self._connection:
            row = self._connection.execute(
                "SELECT id, text, state FROM tasks WHERE id = ? AND archived_date IS NULL",
                (task_id,),
            ).fetchone()
            if row is None:
                raise LookupError(f"No active task with id {task_id}")
            removed = _row_to_task(row)

            cursor = self._connection.execute(
                "DELETE FROM tasks WHERE id = ? AND archived_date IS NULL AND state = 'deleted'",
                (task_id,),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Task {task_id} is not eligible for permanent removal")
        return removed


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(id=row["id"], text=row["text"], state=TaskState(row["state"]))

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from rook.domain.tasks import Task, TaskState


@dataclass(frozen=True, slots=True)
class TaskSnapshot:
    """A permanently-removed Task's row exactly as it existed just before
    removal (Section 8.9), kept only long enough for a same-session undo
    to restore it precisely - including its position, since a restored
    Task must reappear in its original relative order.
    """

    id: int
    text: str
    state: TaskState
    sort_order: int
    created_at: str
    updated_at: str
    state_changed_at: str
    state_date: str


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

    def delete_active_task(self, task_id: int) -> TaskSnapshot:
        """Second-stage delete (Section 15.14): permanently remove a
        Soft-Deleted Task. Returns the row exactly as it existed
        immediately before removal, so a same-session undo (Phase 7) can
        restore it precisely.
        """
        with self._connection:
            row = self._connection.execute(
                """
                SELECT id, text, state, sort_order, created_at, updated_at,
                       state_changed_at, state_date
                FROM tasks
                WHERE id = ? AND archived_date IS NULL
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                raise LookupError(f"No active task with id {task_id}")
            removed = _row_to_snapshot(row)

            cursor = self._connection.execute(
                "DELETE FROM tasks WHERE id = ? AND archived_date IS NULL AND state = 'deleted'",
                (task_id,),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Task {task_id} is not eligible for permanent removal")
        return removed

    def restore_task(self, snapshot: TaskSnapshot) -> Task:
        """Undo of a permanent removal: reinsert the row exactly as
        captured. The restored Task is still Deleted (Section 8.9) -
        undoing a removal does not reopen the Task."""
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO tasks (
                    id, text, state, sort_order, created_at, updated_at,
                    state_changed_at, state_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.text,
                    snapshot.state.value,
                    snapshot.sort_order,
                    snapshot.created_at,
                    snapshot.updated_at,
                    snapshot.state_changed_at,
                    snapshot.state_date,
                ),
            )
        return Task(id=snapshot.id, text=snapshot.text, state=snapshot.state)

    def delete_task_by_id(self, task_id: int) -> None:
        """Unconditional removal used only to undo a same-session Task
        creation (Section 15.19 DeleteCreatedTask). Safe without a state
        guard because single-level undo guarantees no other mutation has
        touched this Task since it was created - otherwise that later
        mutation would have replaced this undo record first.
        """
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM tasks WHERE id = ? AND archived_date IS NULL", (task_id,)
            )
            if cursor.rowcount != 1:
                raise LookupError(f"No active task with id {task_id}")


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(id=row["id"], text=row["text"], state=TaskState(row["state"]))


def _row_to_snapshot(row: sqlite3.Row) -> TaskSnapshot:
    return TaskSnapshot(
        id=row["id"],
        text=row["text"],
        state=TaskState(row["state"]),
        sort_order=row["sort_order"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        state_changed_at=row["state_changed_at"],
        state_date=row["state_date"],
    )

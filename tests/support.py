"""Shared test helpers. Not part of the public package."""

import sqlite3
from collections.abc import Callable, Sequence
from datetime import date, datetime
from pathlib import Path

from rook.domain.tasks import Task
from rook.persistence.database import connect
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.tasks import TaskService


def make_task_service(
    db_path: Path,
    *,
    tasks: Sequence[Task] = (),
    now_provider: Callable[[], datetime] = datetime.now,
    today_provider: Callable[[], date] = date.today,
) -> TaskService:
    """A TaskService backed by a fresh temporary database, pre-seeded with
    the given Tasks (preserving their exact ids, text, and state)."""
    connection = connect(db_path)
    migrate(connection)
    for task in tasks:
        _seed_task(connection, task, now=now_provider(), local_date=today_provider())
    return TaskService(
        TaskRepository(connection), now_provider=now_provider, today_provider=today_provider
    )


def _seed_task(
    connection: sqlite3.Connection, task: Task, *, now: datetime, local_date: date
) -> None:
    timestamp = now.isoformat()
    with connection:
        next_order = connection.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM tasks WHERE archived_date IS NULL"
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO tasks (
                id, text, state, sort_order, created_at, updated_at,
                state_changed_at, state_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.text,
                task.state.value,
                next_order,
                timestamp,
                timestamp,
                timestamp,
                local_date.isoformat(),
            ),
        )

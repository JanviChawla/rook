import sqlite3
from datetime import date, datetime

import pytest

from rook.domain.tasks import Task, TaskState
from rook.persistence.database import connect
from rook.persistence.metadata import MetadataRepository
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.rollover import RolloverService

_NOW = datetime(2026, 7, 24, 9, 0)


def _setup(path):
    connection = connect(path)
    migrate(connection)
    return connection, TaskRepository(connection), MetadataRepository(connection)


def _rollover(connection, metadata, *, today, now=_NOW):
    return RolloverService(
        connection, metadata, today_provider=lambda: today, now_provider=lambda: now
    )


class _FailBeforeMetadataWrite:
    """A connection proxy that fails only the app_meta write, so tests can
    prove the archive/renumber steps roll back too (Section 18.23)."""

    def __init__(self, real_connection: sqlite3.Connection) -> None:
        self._real = real_connection

    def execute(self, sql, *args, **kwargs):
        if "app_meta" in sql:
            raise sqlite3.OperationalError("simulated failure")
        return self._real.execute(sql, *args, **kwargs)

    def __enter__(self):
        return self._real.__enter__()

    def __exit__(self, exc_type, exc, tb):
        return self._real.__exit__(exc_type, exc, tb)

    def __getattr__(self, name):
        return getattr(self._real, name)


def test_no_op_when_current_date_equals_last_processed(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    today = date(2026, 7, 24)
    metadata.set_last_processed_date(today)
    created = tasks.create_task("Task", now=_NOW, local_date=today)
    tasks.set_task_state(created.id, TaskState.COMPLETED, now=_NOW, local_date=today)

    result = _rollover(connection, metadata, today=today).roll_forward_if_needed()

    assert result.changed is False
    assert tasks.list_active_tasks() == [
        Task(id=created.id, text="Task", state=TaskState.COMPLETED)
    ]


def test_open_and_migrated_carry_forward_completed_and_deleted_archive(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)

    open_task = tasks.create_task("Open", now=_NOW, local_date=day1)
    migrated_task = tasks.create_task("Migrated", now=_NOW, local_date=day1)
    tasks.set_task_state(migrated_task.id, TaskState.MIGRATED, now=_NOW, local_date=day1)
    completed_task = tasks.create_task("Completed", now=_NOW, local_date=day1)
    tasks.set_task_state(completed_task.id, TaskState.COMPLETED, now=_NOW, local_date=day1)
    deleted_task = tasks.create_task("Deleted", now=_NOW, local_date=day1)
    tasks.set_task_state(deleted_task.id, TaskState.DELETED, now=_NOW, local_date=day1)

    day2 = date(2026, 7, 24)
    result = _rollover(connection, metadata, today=day2).roll_forward_if_needed()

    assert result.changed is True
    remaining = tasks.list_active_tasks()
    # Task text "Migrated" sorts before "Open" alphabetically (M < O).
    assert [task.id for task in remaining] == [migrated_task.id, open_task.id]
    # Both carry forward as Open — the migration intent from day1 is resolved
    # into a fresh active task on day2.
    assert remaining[0].state == TaskState.OPEN
    assert remaining[1].state == TaskState.OPEN


def test_unresolved_tasks_sorted_alphabetically_after_rollover(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)

    first = tasks.create_task("First open", now=_NOW, local_date=day1)
    completed = tasks.create_task("Will complete", now=_NOW, local_date=day1)
    tasks.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=day1)
    second = tasks.create_task("Second open", now=_NOW, local_date=day1)
    migrated = tasks.create_task("Migrated", now=_NOW, local_date=day1)
    tasks.set_task_state(migrated.id, TaskState.MIGRATED, now=_NOW, local_date=day1)

    day2 = date(2026, 7, 24)
    _rollover(connection, metadata, today=day2).roll_forward_if_needed()

    remaining = tasks.list_active_tasks()
    # Alphabetically: "First open" < "Migrated" < "Second open"
    assert [task.id for task in remaining] == [first.id, migrated.id, second.id]


def test_cross_day_tasks_sorted_alphabetically_after_rollover(tmp_path) -> None:
    """Tasks from multiple days must sort together alphabetically, not in
    per-day groups (issue #6)."""
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 22)
    metadata.set_last_processed_date(day1)

    # Day 1: tasks already in alpha order within their day.
    apple = tasks.create_task("Apple", now=_NOW, local_date=day1)
    zebra = tasks.create_task("Zebra", now=_NOW, local_date=day1)

    day2 = date(2026, 7, 23)
    _rollover(connection, metadata, today=day2).roll_forward_if_needed()

    # Day 2: add a task that falls alphabetically between the day-1 tasks.
    mango = tasks.create_task("Mango", now=_NOW, local_date=day2)

    day3 = date(2026, 7, 24)
    _rollover(connection, metadata, today=day3).roll_forward_if_needed()

    remaining = tasks.list_active_tasks()
    # Cross-day alpha sort: Apple < Mango < Zebra.
    # A per-day sort would produce [Apple, Zebra, Mango] (day-1 group first).
    assert [task.id for task in remaining] == [apple.id, mango.id, zebra.id]


def test_archive_order_is_stable_after_rollover(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)

    first = tasks.create_task("First", now=_NOW, local_date=day1)
    tasks.set_task_state(first.id, TaskState.COMPLETED, now=_NOW, local_date=day1)
    second = tasks.create_task("Second", now=_NOW, local_date=day1)
    tasks.set_task_state(second.id, TaskState.DELETED, now=_NOW, local_date=day1)

    day2 = date(2026, 7, 24)
    _rollover(connection, metadata, today=day2).roll_forward_if_needed()

    rows = connection.execute(
        "SELECT id FROM tasks WHERE archived_date IS NOT NULL ORDER BY archive_order ASC"
    ).fetchall()
    assert [row["id"] for row in rows] == [first.id, second.id]


def test_repeated_rollover_call_does_not_duplicate_archive_rows(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)
    completed = tasks.create_task("Task", now=_NOW, local_date=day1)
    tasks.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=day1)

    day2 = date(2026, 7, 24)
    service = _rollover(connection, metadata, today=day2)
    first_result = service.roll_forward_if_needed()
    second_result = service.roll_forward_if_needed()

    assert first_result.changed is True
    assert second_result.changed is False

    count = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE id = ?", (completed.id,)
    ).fetchone()[0]
    assert count == 1


def test_multiple_missed_days_archive_correctly_without_empty_snapshots(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 20)
    metadata.set_last_processed_date(day1)
    completed = tasks.create_task("Task", now=_NOW, local_date=day1)
    tasks.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=day1)

    much_later = date(2026, 7, 30)  # several days missed in one gap
    result = _rollover(connection, metadata, today=much_later).roll_forward_if_needed()

    assert result.changed is True
    row = connection.execute(
        "SELECT archived_date FROM tasks WHERE id = ?", (completed.id,)
    ).fetchone()
    # Attributed to the Task's own state_date, not the current date or any
    # date in between - no per-day loop, no synthetic snapshots.
    assert row["archived_date"] == day1.isoformat()

    distinct_dates = connection.execute(
        "SELECT DISTINCT archived_date FROM tasks WHERE archived_date IS NOT NULL"
    ).fetchall()
    assert [d["archived_date"] for d in distinct_dates] == [day1.isoformat()]


def test_backward_date_performs_no_rollover(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    later = date(2026, 7, 24)
    metadata.set_last_processed_date(later)
    completed = tasks.create_task("Task", now=_NOW, local_date=later)
    tasks.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=later)

    earlier = date(2026, 7, 20)
    result = _rollover(connection, metadata, today=earlier).roll_forward_if_needed()

    assert result.changed is False
    assert tasks.list_active_tasks() == [
        Task(id=completed.id, text="Task", state=TaskState.COMPLETED)
    ]
    assert metadata.get_last_processed_date() == later


def test_permanently_removed_task_remains_absent_after_rollover(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)
    removed = tasks.create_task("Will be removed", now=_NOW, local_date=day1)
    tasks.set_task_state(removed.id, TaskState.DELETED, now=_NOW, local_date=day1)
    tasks.delete_active_task(removed.id)

    day2 = date(2026, 7, 24)
    result = _rollover(connection, metadata, today=day2).roll_forward_if_needed()

    assert result.changed is True  # the date still advanced
    assert tasks.list_active_tasks() == []
    total_rows = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert total_rows == 0


def test_exception_before_commit_rolls_back_everything(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)
    completed = tasks.create_task("Task", now=_NOW, local_date=day1)
    tasks.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=day1)

    failing_connection = _FailBeforeMetadataWrite(connection)
    day2 = date(2026, 7, 24)
    service = RolloverService(
        failing_connection, metadata, today_provider=lambda: day2, now_provider=lambda: _NOW
    )

    with pytest.raises(sqlite3.OperationalError):
        service.roll_forward_if_needed()

    # The archive update and the metadata write must roll back together.
    assert metadata.get_last_processed_date() == day1
    row = connection.execute(
        "SELECT archived_date FROM tasks WHERE id = ?", (completed.id,)
    ).fetchone()
    assert row["archived_date"] is None


def test_reopen_after_successful_rollover_produces_same_result(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    connection, tasks, metadata = _setup(path)
    day1 = date(2026, 7, 23)
    metadata.set_last_processed_date(day1)
    completed = tasks.create_task("Task", now=_NOW, local_date=day1)
    tasks.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=day1)

    day2 = date(2026, 7, 24)
    _rollover(connection, metadata, today=day2).roll_forward_if_needed()
    first_active = tasks.list_active_tasks()

    reopened_connection = connect(path)
    reopened_tasks = TaskRepository(reopened_connection)
    reopened_metadata = MetadataRepository(reopened_connection)
    _rollover(reopened_connection, reopened_metadata, today=day2).roll_forward_if_needed()

    assert reopened_tasks.list_active_tasks() == first_active == []


def test_first_launch_ever_records_today_without_archiving(tmp_path) -> None:
    connection, tasks, metadata = _setup(tmp_path / "test.sqlite3")
    assert metadata.get_last_processed_date() is None

    today = date(2026, 7, 24)
    result = _rollover(connection, metadata, today=today).roll_forward_if_needed()

    assert result.changed is False
    assert metadata.get_last_processed_date() == today

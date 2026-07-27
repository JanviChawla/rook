"""Tests for archive persistence layer (Section 21.14)."""

import sqlite3
from datetime import date, timedelta

import pytest

from rook.domain.tasks import TaskState
from rook.persistence.archive import ArchiveRepository, week_start_for
from rook.persistence.database import connect
from rook.persistence.migrations import migrate


def _make_connection(tmp_path) -> sqlite3.Connection:
    connection = connect(tmp_path / "test.sqlite3")
    migrate(connection)
    return connection


def _seed_archived(connection: sqlite3.Connection, text: str, state: TaskState, archived_date: date, order: int = 1) -> None:
    ts = "2026-01-01T09:00:00"
    with connection:
        connection.execute(
            """
            INSERT INTO tasks (text, state, sort_order, archive_order, archived_date, archived_at,
                               created_at, updated_at, state_changed_at, state_date)
            VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
            """,
            (text, state.value, order, archived_date.isoformat(), ts, ts, ts, ts, archived_date.isoformat()),
        )


class TestListArchiveDates:
    def test_empty_when_no_archived_tasks(self, tmp_path):
        conn = _make_connection(tmp_path)
        repo = ArchiveRepository(conn)
        assert repo.list_archive_dates() == []

    def test_active_tasks_excluded(self, tmp_path):
        conn = _make_connection(tmp_path)
        ts = "2026-07-24T09:00:00"
        with conn:
            conn.execute(
                "INSERT INTO tasks (text, state, sort_order, created_at, updated_at, state_changed_at, state_date) VALUES (?, ?, 1, ?, ?, ?, ?)",
                ("Active task", TaskState.OPEN.value, ts, ts, ts, "2026-07-24"),
            )
        repo = ArchiveRepository(conn)
        assert repo.list_archive_dates() == []

    def test_returns_unique_dates_newest_first(self, tmp_path):
        conn = _make_connection(tmp_path)
        d1 = date(2026, 7, 20)
        d2 = date(2026, 7, 24)
        _seed_archived(conn, "Task A", TaskState.COMPLETED, d1)
        _seed_archived(conn, "Task B", TaskState.COMPLETED, d2)
        _seed_archived(conn, "Task C", TaskState.DELETED, d1)
        repo = ArchiveRepository(conn)
        assert repo.list_archive_dates() == [d2, d1]

    def test_single_date_returned_once(self, tmp_path):
        conn = _make_connection(tmp_path)
        d = date(2026, 7, 22)
        _seed_archived(conn, "Task A", TaskState.COMPLETED, d, order=1)
        _seed_archived(conn, "Task B", TaskState.COMPLETED, d, order=2)
        repo = ArchiveRepository(conn)
        assert repo.list_archive_dates() == [d]


class TestListWeekItems:
    def test_empty_range(self, tmp_path):
        conn = _make_connection(tmp_path)
        repo = ArchiveRepository(conn)
        result = repo.list_week_items(date(2026, 7, 20), date(2026, 7, 27))
        assert result == []

    def test_tasks_outside_range_excluded(self, tmp_path):
        conn = _make_connection(tmp_path)
        _seed_archived(conn, "Before", TaskState.COMPLETED, date(2026, 7, 19))
        _seed_archived(conn, "After", TaskState.COMPLETED, date(2026, 7, 27))
        repo = ArchiveRepository(conn)
        result = repo.list_week_items(date(2026, 7, 20), date(2026, 7, 27))
        assert result == []

    def test_groups_by_day_oldest_first(self, tmp_path):
        conn = _make_connection(tmp_path)
        d1 = date(2026, 7, 21)
        d2 = date(2026, 7, 23)
        _seed_archived(conn, "D2 task", TaskState.COMPLETED, d2, order=1)
        _seed_archived(conn, "D1 task", TaskState.COMPLETED, d1, order=1)
        repo = ArchiveRepository(conn)
        result = repo.list_week_items(date(2026, 7, 20), date(2026, 7, 27))
        assert len(result) == 2
        assert result[0][0] == d1
        assert result[1][0] == d2

    def test_preserves_archive_order_within_day(self, tmp_path):
        conn = _make_connection(tmp_path)
        d = date(2026, 7, 22)
        _seed_archived(conn, "First", TaskState.COMPLETED, d, order=1)
        _seed_archived(conn, "Second", TaskState.COMPLETED, d, order=2)
        _seed_archived(conn, "Third", TaskState.DELETED, d, order=3)
        repo = ArchiveRepository(conn)
        result = repo.list_week_items(date(2026, 7, 20), date(2026, 7, 27))
        assert len(result) == 1
        day, tasks = result[0]
        assert day == d
        assert [t.text for t in tasks] == ["First", "Second", "Third"]

    def test_includes_completed_and_deleted(self, tmp_path):
        conn = _make_connection(tmp_path)
        d = date(2026, 7, 22)
        _seed_archived(conn, "Done", TaskState.COMPLETED, d, order=1)
        _seed_archived(conn, "Gone", TaskState.DELETED, d, order=2)
        repo = ArchiveRepository(conn)
        result = repo.list_week_items(date(2026, 7, 20), date(2026, 7, 27))
        day, tasks = result[0]
        assert tasks[0].state == TaskState.COMPLETED
        assert tasks[1].state == TaskState.DELETED

    def test_week_end_exclusive(self, tmp_path):
        conn = _make_connection(tmp_path)
        _seed_archived(conn, "On boundary", TaskState.COMPLETED, date(2026, 7, 27))
        repo = ArchiveRepository(conn)
        result = repo.list_week_items(date(2026, 7, 20), date(2026, 7, 27))
        assert result == []


class TestWeekStartFor:
    @pytest.mark.parametrize("d,expected", [
        (date(2026, 7, 27), date(2026, 7, 26)),  # Monday → previous Sunday
        (date(2026, 7, 26), date(2026, 7, 26)),  # Sunday → itself
        (date(2026, 7, 25), date(2026, 7, 19)),  # Saturday → previous Sunday
        (date(2026, 7, 19), date(2026, 7, 19)),  # Sunday → itself
    ])
    def test_sun_sat_mode(self, d, expected):
        assert week_start_for(d, first_weekday=6) == expected

    @pytest.mark.parametrize("d,expected", [
        (date(2026, 7, 27), date(2026, 7, 27)),  # Monday → itself
        (date(2026, 7, 26), date(2026, 7, 20)),  # Sunday → previous Monday
        (date(2026, 7, 25), date(2026, 7, 20)),  # Saturday → previous Monday
        (date(2026, 7, 20), date(2026, 7, 20)),  # Monday → itself
    ])
    def test_mon_sun_mode(self, d, expected):
        assert week_start_for(d, first_weekday=0) == expected

    def test_crosses_month_boundary(self):
        # July 26 (Sun) is in the Sun-Sat week starting June 29
        # Actually June 29 is a Monday in 2026, so Sun-Sat week for June 29 starts June 28
        d = date(2026, 6, 30)  # Tuesday
        result = week_start_for(d, first_weekday=6)
        assert result == date(2026, 6, 28)  # previous Sunday

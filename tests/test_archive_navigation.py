"""Integration tests for ArchiveScreen navigation (Section 21.14)."""

import asyncio
from datetime import date, datetime

from textual.widgets import Static

from rook import branding
from rook.app import RookApp
from rook.domain.tasks import TaskState
from rook.widgets.archive_screen import ArchiveScreen
from tests.support import make_task_service


_DAY_WEEK1 = date(2026, 7, 14)  # Tuesday, Jul 14 — in week Jul 13–19 (Sun-Sat)
_DAY_WEEK2 = date(2026, 7, 22)  # Wednesday, Jul 22 — in week Jul 19–25
_DAY_WEEK3 = date(2026, 7, 27)  # Monday, Jul 27 — in week Jul 26–Aug 1
_TODAY = date(2026, 7, 27)


def _seed_archived(connection, text: str, state: TaskState, archived_date: date, order: int = 1) -> None:
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


def _make_app(tmp_path, *, with_archive_data: bool = True):
    service = make_task_service(
        tmp_path / "test.sqlite3",
        today_provider=lambda: _TODAY,
        now_provider=lambda: datetime(2026, 7, 27, 9, 0),
    )
    conn = service.connection
    if with_archive_data:
        _seed_archived(conn, "Week 1 task", TaskState.COMPLETED, _DAY_WEEK1)
        _seed_archived(conn, "Week 2 done", TaskState.COMPLETED, _DAY_WEEK2, order=1)
        _seed_archived(conn, "Week 2 del", TaskState.DELETED, _DAY_WEEK2, order=2)
        _seed_archived(conn, "Week 3 task", TaskState.COMPLETED, _DAY_WEEK3)
    return RookApp(
        today_provider=lambda: _TODAY,
        task_service=service,
        rollover_service=service.rollover_service,
        connection=conn,
    )


def test_archive_empty_state(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3")
    conn = service.connection
    app = RookApp(
        task_service=service,
        rollover_service=service.rollover_service,
        connection=conn,
    )

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ArchiveScreen)
            header = screen.query_one("#archive-header", Static)
            assert str(header.content) == f"{branding.DISPLAY_NAME.lower()} {branding.ICON}  Archive"
            content = screen.query_one("#archive-content", Static)
            assert "No archived tasks" in str(content.content)

    asyncio.run(scenario())


def test_archive_opens_on_most_recent_week(tmp_path) -> None:
    app = _make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ArchiveScreen)
            header = screen.query_one("#archive-header", Static)
            header_text = str(header.content)
            assert "Archive —" in header_text
            assert "July" in header_text
            assert "2026" in header_text
            # Week 3 task is the most recent: week Jul 26–Aug 1
            assert "26" in header_text or "27" in header_text

    asyncio.run(scenario())


def test_archive_shows_completed_and_deleted_markers(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3")
    conn = service.connection
    d = date(2026, 7, 22)
    _seed_archived(conn, "Done task", TaskState.COMPLETED, d, order=1)
    _seed_archived(conn, "Deleted task", TaskState.DELETED, d, order=2)
    app = RookApp(
        task_service=service,
        rollover_service=service.rollover_service,
        connection=conn,
    )

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ArchiveScreen)
            content = screen.query_one("#archive-content", Static)
            text = str(content.content)
            assert "× Done task" in text
            assert "Deleted task" in text

    asyncio.run(scenario())


def test_archive_escape_returns_to_today(tmp_path) -> None:
    app = _make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, ArchiveScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, ArchiveScreen)

    asyncio.run(scenario())


def test_archive_prev_week_navigates_to_older_content(tmp_path) -> None:
    app = _make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ArchiveScreen)
            header_before = str(screen.query_one("#archive-header", Static).content)
            await pilot.press("left")
            header_after = str(screen.query_one("#archive-header", Static).content)
            assert header_before != header_after

    asyncio.run(scenario())


def test_archive_footer_shows_only_older_on_newest_week(tmp_path) -> None:
    app = _make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ArchiveScreen)
            footer = str(screen.query_one("#archive-footer", Static).content)
            assert "[←] older" in footer
            assert "[→] newer" not in footer
            assert "[Esc] today" in footer

    asyncio.run(scenario())


def test_archive_footer_shows_only_newer_on_oldest_week(tmp_path) -> None:
    app = _make_app(tmp_path)

    async def scenario() -> None:
        async with app.run_test() as pilot:
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ArchiveScreen)
            # Navigate to the oldest week (week 1, 2 presses back from week 3)
            await pilot.press("left")
            await pilot.press("left")
            footer = str(screen.query_one("#archive-footer", Static).content)
            assert "[→] newer" in footer
            assert "[←] older" not in footer

    asyncio.run(scenario())

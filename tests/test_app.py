import asyncio
from datetime import date

from textual.widgets import Static

from rook import branding
from rook.app import RookApp
from rook.domain.tasks import Task, TaskState
from rook.formatting import format_header_date
from rook.widgets.shortcut_footer import TODAY_EMPTY_FOOTER, TODAY_FOOTER, select_footer_text

FIXED_DATE = date(2026, 7, 24)


def _fixed_today() -> date:
    return FIXED_DATE


def test_today_screen_renders_header_and_mascot() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test() as pilot:
            header = pilot.app.query_one("#header", Static)
            mascot_quote = pilot.app.query_one("#mascot-quote", Static)

            expected_header = (
                f"{branding.DISPLAY_NAME} {branding.ICON}  {format_header_date(FIXED_DATE)}"
            )
            expected_mascot_quote = f'{branding.MASCOT}  "{branding.QUOTE}"'

            assert str(header.content) == expected_header
            assert str(mascot_quote.content) == expected_mascot_quote

    asyncio.run(scenario())


def test_populated_today_shows_full_footer_variant_for_default_size() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test() as pilot:
            footer = pilot.app.query_one("#footer", Static)
            expected = select_footer_text(TODAY_FOOTER, app.size.width)
            assert str(footer.content) == expected

    asyncio.run(scenario())


def test_empty_today_shows_reduced_footer_variant() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today, tasks=[])
        async with app.run_test() as pilot:
            footer = pilot.app.query_one("#footer", Static)
            expected = select_footer_text(TODAY_EMPTY_FOOTER, app.size.width)
            assert str(footer.content) == expected

    asyncio.run(scenario())


def test_empty_today_shows_empty_state_message() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today, tasks=[])
        async with app.run_test() as pilot:
            from rook.widgets.task_list import EMPTY_TODAY_MESSAGE, TaskListView

            task_list = pilot.app.query_one("#task-list", TaskListView)
            assert EMPTY_TODAY_MESSAGE in str(task_list.content)

    asyncio.run(scenario())


def test_mixed_state_tasks_render_expected_symbols() -> None:
    tasks = [
        Task(id=1, text="Open task", state=TaskState.OPEN),
        Task(id=2, text="Migrated task", state=TaskState.MIGRATED),
        Task(id=3, text="Completed task", state=TaskState.COMPLETED),
        Task(id=4, text="Deleted task", state=TaskState.DELETED),
    ]

    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today, tasks=tasks)
        async with app.run_test() as pilot:
            from rook.widgets.task_list import TaskListView

            task_list = pilot.app.query_one("#task-list", TaskListView)
            rendered = str(task_list.content)

            assert "• Open task" in rendered
            assert "> Migrated task" in rendered
            assert "× Completed task" in rendered
            assert "• Deleted task" in rendered

    asyncio.run(scenario())


def test_uses_terminal_native_background_and_foreground() -> None:
    """The app must respect the user's existing terminal background
    (Section 11.9-11.10, D-020) rather than force Textual's fixed theme."""

    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test():
            assert app.theme == "ansi-dark"
            theme = app.get_theme(app.theme)
            assert theme is not None
            assert theme.background == "ansi_default"
            assert theme.foreground == "ansi_default"

    asyncio.run(scenario())


def test_pressing_q_quits() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(scenario())

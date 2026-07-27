import asyncio
from datetime import date

from textual.color import Color
from textual.widgets import Static

from rook import branding
from rook.app import RookApp
from rook.domain.tasks import Task, TaskState
from rook.formatting import format_header_date
from rook.widgets.shortcut_footer import TODAY_EMPTY_FOOTER, TODAY_FOOTER, select_footer_text
from rook.widgets.task_list import EMPTY_TODAY_MESSAGE, TaskListView
from rook.widgets.task_row import TaskRow
from tests.support import make_task_service

FIXED_DATE = date(2026, 7, 24)

# Matches the fictional fixture data Phase 2 introduced (Section 19.20).
DEFAULT_TASKS = [
    Task(id=1, text="Finish the client deck", state=TaskState.OPEN),
    Task(id=2, text="Read Chapter 3", state=TaskState.MIGRATED),
    Task(id=3, text="Submit the expense report", state=TaskState.COMPLETED),
    Task(id=4, text="Buy another monitor", state=TaskState.DELETED),
    Task(
        id=5,
        text=(
            "Draft the long-form article explaining the design decisions "
            "behind the terminal journal and its intentionally limited scope"
        ),
        state=TaskState.OPEN,
    ),
]


def _fixed_today() -> date:
    return FIXED_DATE


def test_today_screen_renders_header_and_mascot(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            header = pilot.app.query_one("#header", Static)
            mascot_quote = pilot.app.query_one("#mascot-quote", Static)

            expected_header = (
                f"{branding.DISPLAY_NAME.lower()} {branding.ICON}  {format_header_date(FIXED_DATE)}"
            )
            expected_mascot_quote = f'{branding.MASCOT}  "{branding.QUOTE}"'

            assert str(header.content) == expected_header
            assert str(mascot_quote.content) == expected_mascot_quote

    asyncio.run(scenario())


def test_populated_today_shows_full_footer_variant_for_default_size(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            footer = pilot.app.query_one("#footer", Static)
            expected = select_footer_text(TODAY_FOOTER, app.size.width)
            assert str(footer.content) == expected

    asyncio.run(scenario())


def test_empty_today_shows_reduced_footer_variant(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            footer = pilot.app.query_one("#footer", Static)
            expected = select_footer_text(TODAY_EMPTY_FOOTER, app.size.width)
            assert str(footer.content) == expected

    asyncio.run(scenario())


def test_empty_today_shows_empty_state_message(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            task_list = pilot.app.query_one("#task-list", TaskListView)
            message = task_list.query_one(Static)
            assert EMPTY_TODAY_MESSAGE in str(message.content)

    asyncio.run(scenario())


def test_mixed_state_tasks_render_expected_symbols(tmp_path) -> None:
    tasks = [
        Task(id=1, text="Open task", state=TaskState.OPEN),
        Task(id=2, text="Migrated task", state=TaskState.MIGRATED),
        Task(id=3, text="Completed task", state=TaskState.COMPLETED),
        Task(id=4, text="Deleted task", state=TaskState.DELETED),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            rendered = "\n".join(
                str(row.query_one(Static).content) for row in pilot.app.query(TaskRow)
            )

            assert "• Open task" in rendered
            assert "> Migrated task" in rendered
            assert "× Completed task" in rendered
            assert "• Deleted task" in rendered

    asyncio.run(scenario())


def test_uses_terminal_native_background_and_foreground(tmp_path) -> None:
    """The app must respect the user's existing terminal background
    (Section 11.9-11.10, D-020) rather than force Textual's fixed theme."""
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test():
            assert app.theme == "ansi-dark"
            theme = app.get_theme(app.theme)
            assert theme is not None
            assert theme.background == "ansi_default"
            assert theme.foreground == "ansi_default"

    asyncio.run(scenario())


def test_header_is_bold(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            header = pilot.app.query_one("#header", Static)
            assert header.styles.text_style.bold

    asyncio.run(scenario())


def test_task_list_scrollbar_uses_a_slim_ansi_safe_style(tmp_path) -> None:
    """The "ansi-dark" theme (unlike "ansi-light") doesn't define scrollbar
    colors, so without an explicit override the scrollbar falls back to
    Textual's fixed truecolor default - a chunky, mismatched bar. The thumb
    uses the terminal's own default foreground so it blends with the
    user's existing theme rather than introducing a new color."""
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            task_list = pilot.app.query_one(TaskListView)
            assert task_list.styles.scrollbar_size_vertical == 1
            assert task_list.styles.scrollbar_color == Color.parse("ansi_default")
            assert task_list.styles.scrollbar_background == Color.parse("ansi_default")

    asyncio.run(scenario())


def test_pressing_q_quits(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(scenario())


def _selected_task_ids(app: RookApp) -> list[int]:
    return [row.item.id for row in app.query(TaskRow) if row.selected]


def test_initial_selection_follows_priority_order(tmp_path) -> None:
    """DEFAULT_TASKS' first Open Task (id=1) should be selected on open."""
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test():
            assert _selected_task_ids(app) == [1]

    asyncio.run(scenario())


def test_down_then_up_returns_to_original_selection(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            await pilot.press("down")
            assert _selected_task_ids(app) == [2]
            await pilot.press("up")
            assert _selected_task_ids(app) == [1]

    asyncio.run(scenario())


def test_up_at_first_row_stays_on_first_row(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            await pilot.press("up")
            assert _selected_task_ids(app) == [1]

    asyncio.run(scenario())


def test_down_at_last_row_stays_on_last_row(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            for _ in range(10):
                await pilot.press("down")
            task_list = app.query_one("#task-list", TaskListView)
            last_task_id = task_list._tasks[-1].id
            assert _selected_task_ids(app) == [last_task_id]

    asyncio.run(scenario())


def test_navigation_does_not_mutate_task_state(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            task_list = app.query_one("#task-list", TaskListView)
            states_before = [task.state for task in task_list._tasks]
            await pilot.press("down")
            await pilot.press("down")
            await pilot.press("up")
            assert [task.state for task in task_list._tasks] == states_before

    asyncio.run(scenario())


def test_empty_list_navigation_is_safe(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test() as pilot:
            await pilot.press("down")
            await pilot.press("up")
            # No crash, and no selection to report.
            assert _selected_task_ids(app) == []

    asyncio.run(scenario())


def test_resize_preserves_selection(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=DEFAULT_TASKS)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press("down")
            assert _selected_task_ids(app) == [2]

            await pilot.resize_terminal(60, 16)
            assert _selected_task_ids(app) == [2]

    asyncio.run(scenario())


def test_long_list_scrolls_selected_row_into_view(tmp_path) -> None:
    tasks = [Task(id=i, text=f"Task number {i}", state=TaskState.OPEN) for i in range(1, 31)]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(
            today_provider=_fixed_today,
            task_service=service,
            rollover_service=service.rollover_service,
        )
        async with app.run_test(size=(80, 16)) as pilot:
            task_list = app.query_one("#task-list", TaskListView)
            assert task_list.scroll_offset.y == 0

            for _ in range(25):
                await pilot.press("down")

            assert task_list.scroll_offset.y > 0
            assert _selected_task_ids(app) == [26]

    asyncio.run(scenario())

"""Regression coverage for a real bug: Static widgets default to parsing
Rich console markup, and square brackets are markup syntax. The wide
footer's "[n] new" style hints were silently corrupted until markup was
explicitly disabled for these widgets.
"""

import asyncio

from rich.console import Console
from textual.widgets import Static

from rook.app import RookApp
from rook.domain.tasks import Task, TaskState
from rook.widgets.shortcut_footer import ShortcutFooter
from rook.widgets.task_row import TaskRow
from tests.support import make_task_service


def _render_plain(widget) -> str:
    console = Console(width=200, no_color=True, legacy_windows=False)
    with console.capture() as capture:
        console.print(widget.visual)
    return capture.get()


def test_shortcut_footer_does_not_parse_bracketed_hints_as_markup() -> None:
    footer = ShortcutFooter(has_tasks=True)
    footer.update("[n] new   [e] edit   [q] quit")
    rendered = _render_plain(footer)
    assert "[n] new" in rendered
    assert "[e] edit" in rendered
    assert "[q] quit" in rendered


def test_task_text_with_brackets_is_not_parsed_as_markup(tmp_path) -> None:
    task = Task(id=1, text="Buy [bold]milk[/bold]", state=TaskState.OPEN)
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[task])

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            row = next(iter(pilot.app.query(TaskRow)))
            display = row.query_one(Static)
            rendered = _render_plain(display)
            assert "Buy [bold]milk[/bold]" in rendered

    asyncio.run(scenario())

"""Regression coverage for a real bug: Static widgets default to parsing
Rich console markup, and square brackets are markup syntax. The wide
footer's "[n] new" style hints were silently corrupted until markup was
explicitly disabled for these widgets.
"""

from rich.console import Console

from rook.widgets.shortcut_footer import ShortcutFooter
from rook.widgets.task_list import TaskListView


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


def test_task_list_view_disables_markup_parsing() -> None:
    view = TaskListView([])
    assert view._render_markup is False

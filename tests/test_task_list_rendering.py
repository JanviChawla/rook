from rook.domain.tasks import Task, TaskState
from rook.widgets.task_list import EMPTY_TODAY_MESSAGE, render_task_lines


def test_empty_list_renders_documented_message() -> None:
    text = render_task_lines([], width=80, safe_symbols=False)
    assert str(text) == f"  {EMPTY_TODAY_MESSAGE}"


def test_stored_text_is_not_mutated_for_deleted_task() -> None:
    task = Task(id=1, text="Buy another monitor", state=TaskState.DELETED)
    text = render_task_lines([task], width=80, safe_symbols=False)
    assert "Buy another monitor" in str(text)
    assert "̶" not in str(text)  # no combining strike characters inserted


def test_deleted_task_is_stylized_as_strike_in_preferred_mode() -> None:
    task = Task(id=1, text="Buy another monitor", state=TaskState.DELETED)
    text = render_task_lines([task], width=80, safe_symbols=False)
    assert any("strike" in str(span.style) for span in text.spans)


def test_deleted_task_uses_fallback_symbol_in_safe_mode() -> None:
    task = Task(id=1, text="Buy another monitor", state=TaskState.DELETED)
    text = render_task_lines([task], width=80, safe_symbols=True)
    rendered = str(text)
    assert rendered.startswith("  ~ Buy another monitor")


def test_long_task_wraps_with_hanging_indent() -> None:
    long_text = (
        "Draft the long-form article explaining the design decisions "
        "behind the terminal journal and its intentionally limited scope"
    )
    task = Task(id=1, text=long_text, state=TaskState.OPEN)
    lines = str(render_task_lines([task], width=70, safe_symbols=False)).split("\n")

    assert len(lines) > 1
    assert lines[0].startswith("  • ")
    for continuation in lines[1:]:
        assert continuation.startswith("    ")
        assert not continuation.startswith("     ")


def test_multiple_tasks_each_on_their_own_line_or_lines() -> None:
    tasks = [
        Task(id=1, text="Finish the client deck", state=TaskState.OPEN),
        Task(id=2, text="Read Chapter 3", state=TaskState.MIGRATED),
    ]
    rendered = str(render_task_lines(tasks, width=80, safe_symbols=False))
    lines = rendered.split("\n")
    assert lines[0] == "  • Finish the client deck"
    assert lines[1] == "  > Read Chapter 3"

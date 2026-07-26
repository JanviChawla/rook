from rook.domain.tasks import Task, TaskState
from rook.widgets.task_row import render_task_row_text


def test_unselected_row_has_blank_selection_column() -> None:
    task = Task(id=1, text="Finish the client deck", state=TaskState.OPEN)
    text = render_task_row_text(task, selected=False, width=80, safe_symbols=False)
    assert str(text) == "  • Finish the client deck"


def test_selected_row_shows_cursor_glyph() -> None:
    task = Task(id=1, text="Finish the client deck", state=TaskState.OPEN)
    text = render_task_row_text(task, selected=True, width=80, safe_symbols=False)
    assert str(text) == "❯ • Finish the client deck"


def test_selected_row_uses_fallback_cursor_glyph_in_safe_mode() -> None:
    task = Task(id=1, text="Finish the client deck", state=TaskState.OPEN)
    text = render_task_row_text(task, selected=True, width=80, safe_symbols=True)
    assert str(text) == "> * Finish the client deck"


def test_stored_text_is_not_mutated_for_deleted_task() -> None:
    task = Task(id=1, text="Buy another monitor", state=TaskState.DELETED)
    text = render_task_row_text(task, selected=False, width=80, safe_symbols=False)
    assert "Buy another monitor" in str(text)
    assert "̶" not in str(text)  # no combining strike characters inserted


def test_deleted_task_is_stylized_as_strike_in_preferred_mode() -> None:
    task = Task(id=1, text="Buy another monitor", state=TaskState.DELETED)
    text = render_task_row_text(task, selected=False, width=80, safe_symbols=False)
    assert any("strike" in str(span.style) for span in text.spans)


def test_deleted_task_uses_fallback_symbol_in_safe_mode() -> None:
    task = Task(id=1, text="Buy another monitor", state=TaskState.DELETED)
    text = render_task_row_text(task, selected=False, width=80, safe_symbols=True)
    rendered = str(text)
    assert rendered.startswith("  ~ Buy another monitor")


def test_long_task_wraps_with_hanging_indent() -> None:
    long_text = (
        "Draft the long-form article explaining the design decisions "
        "behind the terminal journal and its intentionally limited scope"
    )
    task = Task(id=1, text=long_text, state=TaskState.OPEN)
    lines = str(render_task_row_text(task, selected=False, width=70, safe_symbols=False)).split(
        "\n"
    )

    assert len(lines) > 1
    assert lines[0].startswith("  • ")
    for continuation in lines[1:]:
        assert continuation.startswith("    ")
        assert not continuation.startswith("     ")

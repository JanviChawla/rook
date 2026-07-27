import asyncio

from textual import events
from textual.widgets import Input, Static

from rook.app import RookApp
from rook.domain.tasks import Task, TaskState
from rook.widgets.shortcut_footer import EDITING_FOOTER_TEXT
from rook.widgets.task_list import TaskListView
from tests.support import make_task_service


def _run(scenario) -> None:
    asyncio.run(scenario)


def _tasks_texts_and_states(task_list: TaskListView) -> list[tuple[str, TaskState]]:
    return [(task.text, task.state) for task in task_list._tasks]


def test_new_task_appends_blank_editable_row_at_the_bottom(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")

            task_list = app.query_one(TaskListView)
            assert _tasks_texts_and_states(task_list)[-1] == ("", TaskState.OPEN)

            editor = app.query_one(Input)
            assert editor.value == ""
            assert editor.has_focus

            footer = app.query_one("#footer", Static)
            assert str(footer.content) == EDITING_FOOTER_TEXT

    _run(scenario())


def test_editor_cursor_uses_reversed_terminal_default_colors(tmp_path) -> None:
    """The text-entry cursor must be a filled block using the terminal's
    own default foreground (reversed) rather than "ansi-dark"'s hardcoded
    ansi_black on ansi_bright_white, which many custom terminal palettes
    remap to something unrelated to the terminal's actual foreground."""
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            editor = app.query_one(Input)
            cursor_style = editor.get_component_rich_style("input--cursor")
            assert cursor_style.reverse is True

    _run(scenario())


def test_create_and_save_a_task_then_end_chain_with_escape(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            for character in "Buy groceries":
                await pilot.press(character)
            await pilot.press("enter")

            task_list = app.query_one(TaskListView)
            # Section 6.5: the Task is saved, and creation mode continues
            # with a fresh blank row rather than returning to navigation.
            assert ("Buy groceries", TaskState.OPEN) in _tasks_texts_and_states(task_list)
            assert task_list._editing_task_id is not None

            editor = app.query_one(Input)
            assert editor.value == ""
            assert editor.has_focus

            footer = app.query_one("#footer", Static)
            assert str(footer.content) == EDITING_FOOTER_TEXT

            # Ending the chain leaves only the already-saved Task.
            await pilot.press("escape")
            assert _tasks_texts_and_states(task_list)[-1] == ("Buy groceries", TaskState.OPEN)
            assert task_list._editing_task_id is None
            assert not list(app.query(Input))

    _run(scenario())


def test_enter_after_save_chains_to_another_blank_task(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            for character in "First task":
                await pilot.press(character)
            await pilot.press("enter")
            for character in "Second task":
                await pilot.press(character)
            await pilot.press("enter")

            task_list = app.query_one(TaskListView)
            texts_and_states = _tasks_texts_and_states(task_list)
            assert ("First task", TaskState.OPEN) in texts_and_states
            assert ("Second task", TaskState.OPEN) in texts_and_states
            assert len(texts_and_states) == 3  # two saved + the still-open blank

            editor = app.query_one(Input)
            assert editor.value == ""
            assert editor.has_focus

    _run(scenario())


def test_escape_mid_chain_only_discards_current_blank(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            for character in "First task":
                await pilot.press(character)
            await pilot.press("enter")  # saved; chain continues with a new blank

            first_task_id = app.query_one(TaskListView)._tasks[0].id

            for character in "abc":
                await pilot.press(character)
            await pilot.press("escape")  # cancel only this second, unsaved blank

            task_list = app.query_one(TaskListView)
            assert _tasks_texts_and_states(task_list) == [("First task", TaskState.OPEN)]
            assert task_list.selected_task_id == first_task_id
            assert task_list._editing_task_id is None
            assert not list(app.query(Input))

    _run(scenario())


def test_blank_enter_ends_chain_keeping_earlier_saved_task(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            for character in "First task":
                await pilot.press(character)
            await pilot.press("enter")  # saved; chain continues
            await pilot.press("enter")  # blank Enter ends the chain

            task_list = app.query_one(TaskListView)
            assert _tasks_texts_and_states(task_list) == [("First task", TaskState.OPEN)]
            assert task_list._editing_task_id is None
            assert not list(app.query(Input))

    _run(scenario())


def test_cancel_new_task_with_escape_leaves_no_blank_row(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            task_list = app.query_one(TaskListView)
            count_before = len(task_list._tasks)

            await pilot.press("n")
            for character in "abc":
                await pilot.press(character)
            await pilot.press("escape")

            assert len(task_list._tasks) == count_before
            assert not list(app.query(Input))
            assert task_list.selected_task_id == 1

    _run(scenario())


def test_cancel_empty_new_task_with_backspace(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            task_list = app.query_one(TaskListView)
            count_before = len(task_list._tasks)

            await pilot.press("n")
            await pilot.press("backspace")

            assert len(task_list._tasks) == count_before
            assert not list(app.query(Input))
            assert task_list.selected_task_id == 1

    _run(scenario())


def test_enter_on_blank_new_task_cancels_silently(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            task_list = app.query_one(TaskListView)
            count_before = len(task_list._tasks)

            await pilot.press("n")
            await pilot.press("enter")

            assert len(task_list._tasks) == count_before
            assert not list(app.query(Input))
            status = app.query_one("#status", Static)
            assert str(status.content) == ""

    _run(scenario())


def test_edit_and_save_an_existing_task(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Old text", state=TaskState.MIGRATED)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")

            editor = app.query_one(Input)
            assert editor.value == "Old text"
            assert editor.cursor_position == len("Old text")

            for _ in "Old text":
                await pilot.press("backspace")
            for character in "New text":
                await pilot.press(character)
            await pilot.press("enter")

            task_list = app.query_one(TaskListView)
            assert _tasks_texts_and_states(task_list) == [("New text", TaskState.MIGRATED)]

    _run(scenario())


def test_enter_from_navigation_also_edits_the_selected_task(tmp_path) -> None:
    """Section 9.3/9.10: Enter is a second way to trigger the same edit
    action as `e` from Today's navigation mode - not a different action."""
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("enter")

            editor = app.query_one(Input)
            assert editor.value == "Task"
            assert editor.has_focus

            task_list = app.query_one(TaskListView)
            assert task_list._editing_task_id == 1

    _run(scenario())


def test_edit_and_cancel_an_existing_task_restores_original_text(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Original", state=TaskState.COMPLETED)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            for character in "junk":
                await pilot.press(character)
            await pilot.press("escape")

            task_list = app.query_one(TaskListView)
            assert _tasks_texts_and_states(task_list) == [("Original", TaskState.COMPLETED)]
            assert not list(app.query(Input))

    _run(scenario())


def test_saving_blank_existing_task_is_rejected_and_stays_in_edit_mode(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Original", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            for _ in "Original":
                await pilot.press("backspace")
            await pilot.press("enter")

            task_list = app.query_one(TaskListView)
            assert _tasks_texts_and_states(task_list) == [("Original", TaskState.OPEN)]
            assert task_list._editing_task_id == 1

            status = app.query_one("#status", Static)
            assert str(status.content) == "Task cannot be blank."

            editor = app.query_one(Input)
            assert editor.has_focus

    _run(scenario())


def test_backspace_on_empty_existing_edit_does_not_cancel(tmp_path) -> None:
    """Section 9.5: unlike creation, editing an existing Task down to
    empty and pressing Backspace again must not delete or exit."""
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="X", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.press("backspace")  # empties the field
            await pilot.press("backspace")  # pressed again on empty

            task_list = app.query_one(TaskListView)
            assert task_list._editing_task_id == 1
            assert list(app.query(Input))

    _run(scenario())


def test_shortcut_letters_and_migrate_symbol_insert_as_text_while_editing(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="x", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.press("backspace")  # clear the seeded placeholder text
            for character in "nexdura?q>":
                await pilot.press(character)

            editor = app.query_one(Input)
            assert editor.value == "nexdura?q>"
            # Still editing: none of those keys triggered navigation/quit/etc.
            task_list = app.query_one(TaskListView)
            assert task_list._editing_task_id == 1

    _run(scenario())


def test_pasting_multiline_text_normalizes_to_single_line(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            editor = app.query_one(Input)
            editor.post_message(events.Paste("Line one\nLine two\r\nLine three"))
            await pilot.pause()
            assert editor.value == "Line one Line two Line three"

    _run(scenario())


def test_text_length_is_capped_at_1000_code_points(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Existing task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            editor = app.query_one(Input)
            editor.insert_text_at_cursor("a" * 1000)
            assert len(editor.value) == 1000

            # Section 18.5: additional input beyond the limit is rejected;
            # existing confirmed text remains intact.
            editor.insert_text_at_cursor("b")
            assert len(editor.value) == 1000
            assert editor.value == "a" * 1000

    _run(scenario())


def test_up_down_are_ignored_while_editing(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.OPEN),
        Task(id=2, text="Second", state=TaskState.OPEN),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.press("down")
            task_list = app.query_one(TaskListView)
            assert task_list.selected_task_id == 1
            assert task_list._editing_task_id == 1

    _run(scenario())

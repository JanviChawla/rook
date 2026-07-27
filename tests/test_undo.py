import asyncio

import pytest
from textual.widgets import Static

from rook.app import RookApp
from rook.domain.tasks import Task, TaskState
from rook.persistence.database import connect
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.tasks import TaskService
from rook.widgets.task_list import TaskListView
from tests.support import make_task_service


def _run(scenario) -> None:
    asyncio.run(scenario)


def test_undo_creation_removes_the_created_task(tmp_path) -> None:
    service = make_task_service(tmp_path / "test.sqlite3", tasks=[])

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("n")
            for character in "New task":
                await pilot.press(character)
            await pilot.press("enter")  # saved; chain continues with a new blank
            await pilot.press("escape")  # end the chain, back to navigation

            task_list = app.query_one(TaskListView)
            assert [task.text for task in task_list._tasks] == ["New task"]

            await pilot.press("u")
            assert task_list._tasks == []

    _run(scenario())


def test_undo_edit_restores_text(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Original", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            for _ in "Original":
                await pilot.press("backspace")
            for character in "Changed":
                await pilot.press(character)
            await pilot.press("enter")

            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].text == "Changed"

            await pilot.press("u")
            assert task_list._tasks[0].text == "Original"

    _run(scenario())


@pytest.mark.parametrize(
    ("key", "initial_state"),
    [
        ("x", TaskState.OPEN),
        ("x", TaskState.MIGRATED),
        ("x", TaskState.COMPLETED),
        ("x", TaskState.DELETED),
        (">", TaskState.OPEN),
        (">", TaskState.MIGRATED),
        (">", TaskState.COMPLETED),
        (">", TaskState.DELETED),
        ("d", TaskState.OPEN),
        ("d", TaskState.MIGRATED),
        ("d", TaskState.COMPLETED),
    ],
)
def test_undo_state_change_restores_prior_state(tmp_path, key, initial_state) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=initial_state)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press(key)
            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state != initial_state  # sanity: it actually changed

            await pilot.press("u")
            assert task_list._tasks[0].state == initial_state

    _run(scenario())


def test_undo_permanent_removal_restores_original_position(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.OPEN),
        Task(id=2, text="Second", state=TaskState.DELETED),
        Task(id=3, text="Third", state=TaskState.OPEN),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("down")  # select id=2
            task_list = app.query_one(TaskListView)
            assert task_list.selected_task_id == 2

            await pilot.press("d")  # already Deleted: permanent removal
            assert [task.id for task in task_list._tasks] == [1, 3]

            await pilot.press("u")
            assert [task.id for task in task_list._tasks] == [1, 2, 3]
            assert task_list._tasks[1].text == "Second"
            assert task_list._tasks[1].state == TaskState.DELETED
            assert task_list.selected_task_id == 2

    _run(scenario())


def test_new_mutation_replaces_pending_undo(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.OPEN),
        Task(id=2, text="Second", state=TaskState.OPEN),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("x")  # completes id=1
            await pilot.press("down")
            await pilot.press("x")  # completes id=2; replaces the pending undo

            task_list = app.query_one(TaskListView)
            await pilot.press("u")
            assert task_list._tasks[0].state == TaskState.COMPLETED  # id=1 untouched
            assert task_list._tasks[1].state == TaskState.OPEN  # id=2's completion undone

    _run(scenario())


def test_navigation_does_not_replace_pending_undo(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.OPEN),
        Task(id=2, text="Second", state=TaskState.OPEN),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("x")  # completes id=1
            await pilot.press("down")
            await pilot.press("up")  # navigate around; must not clear the undo record

            task_list = app.query_one(TaskListView)
            await pilot.press("u")
            assert task_list._tasks[0].state == TaskState.OPEN

    _run(scenario())


def test_nothing_to_undo_message_when_absent(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("u")
            status = app.query_one("#status", Static)
            assert str(status.content) == "Nothing to undo."

            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == TaskState.OPEN

    _run(scenario())


def test_restart_clears_undo(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    service = make_task_service(path, tasks=[Task(id=1, text="Task", state=TaskState.OPEN)])

    async def first_session() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("x")  # completes id=1; recorded only in this session's UndoManager

    _run(first_session())

    # A "restart": a brand new connection/service/App, mirroring how the
    # real process would reopen the same database file after relaunch.
    connection = connect(path)
    migrate(connection)
    fresh_service = TaskService(TaskRepository(connection))

    async def second_session() -> None:
        app = RookApp(task_service=fresh_service)
        async with app.run_test() as pilot:
            await pilot.press("u")
            status = app.query_one("#status", Static)
            assert str(status.content) == "Nothing to undo."

            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == TaskState.COMPLETED  # the mutation persisted

    _run(second_session())


def test_failed_undo_leaves_database_and_ui_consistent(tmp_path) -> None:
    connection = connect(tmp_path / "test.sqlite3")
    migrate(connection)
    service = TaskService(TaskRepository(connection))
    service.create_task("Task")

    async def scenario() -> None:
        app = RookApp(task_service=service)
        async with app.run_test() as pilot:
            await pilot.press("x")  # completes id=1; records an undo

            connection.close()  # simulate persistence becoming unavailable

            await pilot.press("u")
            status = app.query_one("#status", Static)
            assert "Could not save" in str(status.content)

            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == TaskState.COMPLETED  # unchanged: undo failed

    _run(scenario())

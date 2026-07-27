import asyncio
from datetime import date

import pytest
from textual.widgets import Input, Static

from rook.app import RookApp
from rook.domain.tasks import Task, TaskState
from rook.persistence.database import connect
from rook.persistence.metadata import MetadataRepository
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.rollover import RolloverService
from rook.services.tasks import TaskService
from rook.widgets.shortcut_footer import TODAY_EMPTY_FOOTER, select_footer_text
from rook.widgets.task_list import TaskListView
from tests.support import make_task_service


def _run(scenario) -> None:
    asyncio.run(scenario)


# --- Section 8.10 transition table -----------------------------------------


@pytest.mark.parametrize(
    ("initial_state", "expected"),
    [
        (TaskState.OPEN, TaskState.COMPLETED),
        (TaskState.MIGRATED, TaskState.COMPLETED),
        (TaskState.COMPLETED, TaskState.OPEN),
        (TaskState.DELETED, TaskState.COMPLETED),
    ],
)
def test_x_transition_table(tmp_path, initial_state, expected) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=initial_state)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("x")
            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == expected

    _run(scenario())


@pytest.mark.parametrize(
    ("initial_state", "expected"),
    [
        (TaskState.OPEN, TaskState.MIGRATED),
        (TaskState.MIGRATED, TaskState.OPEN),
        (TaskState.COMPLETED, TaskState.MIGRATED),
        (TaskState.DELETED, TaskState.MIGRATED),
    ],
)
def test_migrate_transition_table(tmp_path, initial_state, expected) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=initial_state)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press(">")
            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == expected

    _run(scenario())


@pytest.mark.parametrize("initial_state", [TaskState.OPEN, TaskState.MIGRATED, TaskState.COMPLETED])
def test_d_soft_deletes_non_deleted_task(tmp_path, initial_state) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=initial_state)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("d")
            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == TaskState.DELETED
            assert task_list._tasks[0].text == "Task"  # stored text unmodified
            assert len(task_list._tasks) == 1

    _run(scenario())


def test_second_d_permanently_removes(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    service = make_task_service(path, tasks=[Task(id=1, text="Gone soon", state=TaskState.DELETED)])

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("d")
            task_list = app.query_one(TaskListView)
            assert task_list._tasks == []

    _run(scenario())

    # Confirm it's actually gone from the database, not just the in-memory list.
    connection = connect(path)
    migrate(connection)
    assert TaskRepository(connection).list_active_tasks() == []


# --- Additional required behavior -------------------------------------------


def test_state_change_survives_restart(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    service = make_task_service(path, tasks=[Task(id=1, text="Task", state=TaskState.OPEN)])

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("x")

    _run(scenario())

    connection = connect(path)
    migrate(connection)
    assert TaskRepository(connection).list_active_tasks() == [
        Task(id=1, text="Task", state=TaskState.COMPLETED)
    ]


def test_state_change_does_not_move_the_row(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.OPEN),
        Task(id=2, text="Second", state=TaskState.OPEN),
        Task(id=3, text="Third", state=TaskState.OPEN),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("down")  # selects id=2
            await pilot.press("x")
            task_list = app.query_one(TaskListView)
            assert [task.id for task in task_list._tasks] == [1, 2, 3]
            assert task_list._tasks[1].state == TaskState.COMPLETED

    _run(scenario())


def test_selection_after_removal_chooses_next(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.DELETED),
        Task(id=2, text="Second", state=TaskState.OPEN),
        Task(id=3, text="Third", state=TaskState.OPEN),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("up")  # initial selection is id=2 (first Open); move to id=1
            task_list = app.query_one(TaskListView)
            assert task_list.selected_task_id == 1

            await pilot.press("d")  # id=1 already Deleted: permanent removal
            assert [task.id for task in task_list._tasks] == [2, 3]
            assert task_list.selected_task_id == 2

    _run(scenario())


def test_selection_after_removal_chooses_previous_when_no_next(tmp_path) -> None:
    tasks = [
        Task(id=1, text="First", state=TaskState.OPEN),
        Task(id=2, text="Second", state=TaskState.OPEN),
        Task(id=3, text="Third", state=TaskState.DELETED),
    ]
    service = make_task_service(tmp_path / "test.sqlite3", tasks=tasks)

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("down")
            await pilot.press("down")  # selects id=3, the last row
            task_list = app.query_one(TaskListView)
            assert task_list.selected_task_id == 3

            await pilot.press("d")  # id=3 already Deleted: permanent removal
            assert [task.id for task in task_list._tasks] == [1, 2]
            assert task_list.selected_task_id == 2

    _run(scenario())


def test_selection_after_removing_the_only_task_is_empty(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Only", state=TaskState.DELETED)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("d")
            task_list = app.query_one(TaskListView)
            assert task_list._tasks == []
            assert task_list.selected_task_id is None

            footer = app.query_one("#footer", Static)
            expected = select_footer_text(TODAY_EMPTY_FOOTER, app.size.width)
            assert str(footer.content) == expected

    _run(scenario())


def test_state_change_failure_leaves_visual_state_unchanged(tmp_path) -> None:
    connection = connect(tmp_path / "test.sqlite3")
    migrate(connection)
    metadata = MetadataRepository(connection)
    metadata.set_last_processed_date(date.today())
    service = TaskService(TaskRepository(connection))
    rollover_service = RolloverService(connection, metadata)
    service.create_task("Task")

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=rollover_service)
        async with app.run_test() as pilot:
            connection.close()  # simulate persistence becoming unavailable

            await pilot.press("x")

            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == TaskState.OPEN

            status = app.query_one("#status", Static)
            assert "Could not save" in str(status.content)

    _run(scenario())


def test_state_keys_are_inert_while_editing(tmp_path) -> None:
    service = make_task_service(
        tmp_path / "test.sqlite3", tasks=[Task(id=1, text="Task", state=TaskState.OPEN)]
    )

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=service.rollover_service)
        async with app.run_test() as pilot:
            await pilot.press("e")
            for character in "x>d":
                await pilot.press(character)

            editor = app.query_one(Input)
            assert editor.value == "Taskx>d"

            task_list = app.query_one(TaskListView)
            assert task_list._tasks[0].state == TaskState.OPEN

    _run(scenario())

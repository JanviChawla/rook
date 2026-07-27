import asyncio
from datetime import date, datetime

from textual.widgets import Static

from rook.app import RookApp
from rook.domain.tasks import TaskState
from rook.formatting import format_header_date
from rook.persistence.database import connect
from rook.persistence.metadata import MetadataRepository
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.rollover import RolloverService
from rook.services.tasks import TaskService
from rook.widgets.task_list import TaskListView

_NOW = datetime(2026, 7, 23, 9, 0)
_DAY1 = date(2026, 7, 23)
_DAY2 = date(2026, 7, 24)


class _MutableToday:
    """A today_provider whose value can change mid-test, simulating the
    calendar date actually advancing while the app stays open."""

    def __init__(self, value: date) -> None:
        self.value = value

    def __call__(self) -> date:
        return self.value


def _build(path):
    connection = connect(path)
    migrate(connection)
    metadata = MetadataRepository(connection)
    metadata.set_last_processed_date(_DAY1)
    task_repository = TaskRepository(connection)

    completed = task_repository.create_task("Finish report", now=_NOW, local_date=_DAY1)
    task_repository.set_task_state(completed.id, TaskState.COMPLETED, now=_NOW, local_date=_DAY1)
    open_task = task_repository.create_task("Ongoing", now=_NOW, local_date=_DAY1)

    clock = _MutableToday(_DAY1)
    task_service = TaskService(task_repository, today_provider=clock)
    rollover_service = RolloverService(connection, metadata, today_provider=clock)
    return clock, task_service, rollover_service, completed.id, open_task.id


def test_background_check_applies_rollover_and_refreshes_today(tmp_path) -> None:
    clock, task_service, rollover_service, completed_id, open_id = _build(tmp_path / "test.sqlite3")

    async def scenario() -> None:
        app = RookApp(
            today_provider=clock, task_service=task_service, rollover_service=rollover_service
        )
        async with app.run_test() as pilot:
            task_list = app.query_one(TaskListView)
            assert {task.id for task in task_list._tasks} == {completed_id, open_id}

            # Migrating (not completing) open_id creates a pending undo
            # without making it archive-eligible, so it should still carry
            # forward through the rollover triggered below.
            await pilot.press(">")
            clock.value = _DAY2  # the calendar date advances while the app stays open

            await app._check_for_new_day()

            assert [task.id for task in task_list._tasks] == [open_id]
            assert task_list._tasks[0].state == TaskState.MIGRATED

            header = app.query_one("#header", Static)
            assert format_header_date(_DAY2) in str(header.content)

            await pilot.press("u")
            status = app.query_one("#status", Static)
            assert str(status.content) == "Nothing to undo."

    asyncio.run(scenario())


def test_active_edit_defers_visible_rollover(tmp_path) -> None:
    clock, task_service, rollover_service, completed_id, open_id = _build(tmp_path / "test.sqlite3")

    async def scenario() -> None:
        app = RookApp(
            today_provider=clock, task_service=task_service, rollover_service=rollover_service
        )
        async with app.run_test() as pilot:
            await pilot.press("n")  # begin creating: TaskListView.is_editing is now True
            clock.value = _DAY2

            await app._check_for_new_day()

            task_list = app.query_one(TaskListView)
            assert completed_id in {task.id for task in task_list._tasks}  # not yet archived
            assert app._rollover_pending is True

            await pilot.press("escape")  # end the edit; the deferred rollover runs now

            assert completed_id not in {task.id for task in task_list._tasks}
            assert app._rollover_pending is False

    asyncio.run(scenario())

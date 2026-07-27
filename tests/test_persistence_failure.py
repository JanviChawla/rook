import asyncio
from datetime import date

from textual.widgets import Input, Static

from rook.app import RookApp
from rook.persistence.database import connect
from rook.persistence.metadata import MetadataRepository
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.rollover import RolloverService
from rook.services.tasks import TaskService
from rook.widgets.task_list import TaskListView


def test_write_failure_during_creation_keeps_ui_and_domain_state_consistent(tmp_path) -> None:
    """FR-104: a failed write must never be shown as if it had succeeded,
    and the user's in-progress text must not be silently lost."""
    connection = connect(tmp_path / "test.sqlite3")
    migrate(connection)
    metadata = MetadataRepository(connection)
    metadata.set_last_processed_date(date.today())
    service = TaskService(TaskRepository(connection))
    rollover_service = RolloverService(connection, metadata)

    async def scenario() -> None:
        app = RookApp(task_service=service, rollover_service=rollover_service)
        async with app.run_test() as pilot:
            connection.close()  # simulate persistence becoming unavailable

            await pilot.press("n")
            for character in "Buy milk":
                await pilot.press(character)
            await pilot.press("enter")

            status = app.query_one("#status", Static)
            assert "Could not save" in str(status.content)

            task_list = app.query_one(TaskListView)
            assert task_list._editing_task_id is not None
            assert not any(task.text == "Buy milk" for task in task_list._tasks)

            editor = app.query_one(Input)
            assert editor.value == "Buy milk"
            assert editor.has_focus

    asyncio.run(scenario())

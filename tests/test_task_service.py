import sqlite3
from pathlib import Path

import pytest

from rook.persistence.database import connect
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository
from rook.services.tasks import PersistenceError, TaskService


def _service(path: Path) -> tuple[TaskService, sqlite3.Connection]:
    connection = connect(path)
    migrate(connection)
    return TaskService(TaskRepository(connection)), connection


def test_create_and_list_tasks_through_the_service(tmp_path) -> None:
    service, _ = _service(tmp_path / "test.sqlite3")
    created = service.create_task("Buy milk")

    assert created.text == "Buy milk"
    assert [task.text for task in service.list_active_tasks()] == ["Buy milk"]


def test_write_failure_raises_persistence_error_without_corrupting_stored_state(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    service, connection = _service(path)
    service.create_task("Existing task")

    connection.close()  # simulate the database becoming unavailable mid-session

    with pytest.raises(PersistenceError):
        service.create_task("This must not be saved")

    reopened_service, _ = _service(path)
    assert [task.text for task in reopened_service.list_active_tasks()] == ["Existing task"]

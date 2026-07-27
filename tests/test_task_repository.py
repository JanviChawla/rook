from datetime import date, datetime
from pathlib import Path

import pytest

from rook.domain.tasks import Task, TaskState
from rook.persistence.database import connect
from rook.persistence.migrations import migrate
from rook.persistence.tasks import TaskRepository

_NOW = datetime(2026, 7, 24, 9, 0)
_TODAY = date(2026, 7, 24)


def _repository(path: Path) -> TaskRepository:
    connection = connect(path)
    migrate(connection)
    return TaskRepository(connection)


def test_create_task_and_reload_from_a_new_repository_instance(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    created = _repository(path).create_task("Buy groceries", now=_NOW, local_date=_TODAY)

    reloaded = _repository(path).list_active_tasks()  # a fresh connection, same file
    assert reloaded == [Task(id=created.id, text="Buy groceries", state=TaskState.OPEN)]


def test_edit_task_and_reload(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    created = repository.create_task("Draft", now=_NOW, local_date=_TODAY)
    repository.update_task_text(created.id, "Final draft", now=_NOW)

    reloaded = _repository(path).list_active_tasks()
    assert reloaded == [Task(id=created.id, text="Final draft", state=TaskState.OPEN)]


def test_stable_order_after_restart(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    first = repository.create_task("First", now=_NOW, local_date=_TODAY)
    second = repository.create_task("Second", now=_NOW, local_date=_TODAY)
    third = repository.create_task("Third", now=_NOW, local_date=_TODAY)

    reloaded = _repository(path).list_active_tasks()
    assert [task.id for task in reloaded] == [first.id, second.id, third.id]


def test_unicode_round_trip(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    text = "Buy 牛奶 and café crème — naïve résumé 🎉"
    _repository(path).create_task(text, now=_NOW, local_date=_TODAY)

    reloaded = _repository(path).list_active_tasks()
    assert reloaded[0].text == text


def test_quotes_apostrophes_and_sql_like_text_stored_safely(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    tricky_text = "O'Brien's \"quote\" test'; DROP TABLE tasks; --"
    _repository(path).create_task(tricky_text, now=_NOW, local_date=_TODAY)

    # If this text were ever concatenated into SQL instead of parameterized,
    # the DROP TABLE fragment would have executed and this table would be
    # gone. Reading it back intact proves the query was parameterized.
    reloaded = _repository(path).list_active_tasks()
    assert reloaded[0].text == tricky_text


def test_temporary_databases_are_isolated_from_each_other(tmp_path) -> None:
    repository_a = _repository(tmp_path / "a.sqlite3")
    repository_b = _repository(tmp_path / "b.sqlite3")

    repository_a.create_task("Only in A", now=_NOW, local_date=_TODAY)

    assert [task.text for task in repository_a.list_active_tasks()] == ["Only in A"]
    assert repository_b.list_active_tasks() == []


def test_set_task_state_persists_and_reloads(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    created = repository.create_task("Read Chapter 3", now=_NOW, local_date=_TODAY)

    updated = repository.set_task_state(created.id, TaskState.MIGRATED, now=_NOW, local_date=_TODAY)
    assert updated.state == TaskState.MIGRATED

    reloaded = _repository(path).list_active_tasks()
    assert reloaded == [Task(id=created.id, text="Read Chapter 3", state=TaskState.MIGRATED)]


def test_delete_active_task_removes_row_and_returns_prior_data(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    created = repository.create_task("Buy another monitor", now=_NOW, local_date=_TODAY)
    repository.set_task_state(created.id, TaskState.DELETED, now=_NOW, local_date=_TODAY)

    removed = repository.delete_active_task(created.id)
    assert removed.id == created.id
    assert removed.text == "Buy another monitor"
    assert removed.state == TaskState.DELETED
    assert removed.sort_order is not None
    assert removed.created_at == _NOW.isoformat()
    assert removed.state_date == _TODAY.isoformat()

    reloaded = _repository(path).list_active_tasks()
    assert reloaded == []


def test_delete_active_task_rejects_a_task_that_is_not_soft_deleted(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    created = repository.create_task("Still open", now=_NOW, local_date=_TODAY)

    with pytest.raises(LookupError):
        repository.delete_active_task(created.id)

    # Rejected removal must not have touched the row.
    reloaded = _repository(path).list_active_tasks()
    assert reloaded == [Task(id=created.id, text="Still open", state=TaskState.OPEN)]


def test_restore_task_reinserts_the_exact_row(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    created = repository.create_task("Buy another monitor", now=_NOW, local_date=_TODAY)
    repository.set_task_state(created.id, TaskState.DELETED, now=_NOW, local_date=_TODAY)
    snapshot = repository.delete_active_task(created.id)

    restored = repository.restore_task(snapshot)
    assert restored == Task(id=created.id, text="Buy another monitor", state=TaskState.DELETED)

    reloaded = _repository(path).list_active_tasks()
    assert reloaded == [Task(id=created.id, text="Buy another monitor", state=TaskState.DELETED)]


def test_delete_task_by_id_removes_regardless_of_state(tmp_path) -> None:
    path = tmp_path / "test.sqlite3"
    repository = _repository(path)
    created = repository.create_task("Brand new", now=_NOW, local_date=_TODAY)  # still Open

    repository.delete_task_by_id(created.id)

    reloaded = _repository(path).list_active_tasks()
    assert reloaded == []


def test_delete_task_by_id_raises_if_task_does_not_exist(tmp_path) -> None:
    repository = _repository(tmp_path / "test.sqlite3")

    with pytest.raises(LookupError):
        repository.delete_task_by_id(999)

from rook.domain.tasks import TaskState
from rook.services.undo import DeleteCreatedTask, RestoreTaskState, UndoManager


def test_fresh_manager_has_no_undo() -> None:
    manager = UndoManager()
    assert manager.has_undo is False
    assert manager.take() is None


def test_record_then_take_returns_and_clears() -> None:
    manager = UndoManager()
    manager.record(DeleteCreatedTask(task_id=1))
    assert manager.has_undo is True

    command = manager.take()
    assert command == DeleteCreatedTask(task_id=1)
    assert manager.has_undo is False
    assert manager.take() is None


def test_recording_a_new_command_replaces_the_old_one() -> None:
    manager = UndoManager()
    manager.record(DeleteCreatedTask(task_id=1))
    manager.record(RestoreTaskState(task_id=2, state=TaskState.OPEN))

    assert manager.take() == RestoreTaskState(task_id=2, state=TaskState.OPEN)


def test_clear_removes_pending_command() -> None:
    manager = UndoManager()
    manager.record(DeleteCreatedTask(task_id=1))
    manager.clear()
    assert manager.has_undo is False

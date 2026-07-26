from rook.domain.tasks import Task, TaskState, initial_selection


def test_no_tasks_selects_nothing() -> None:
    assert initial_selection([]) is None


def test_prefers_first_open_task_even_when_it_is_not_the_first_row() -> None:
    tasks = [
        Task(id=1, text="Completed first", state=TaskState.COMPLETED),
        Task(id=2, text="Migrated second", state=TaskState.MIGRATED),
        Task(id=3, text="Open third", state=TaskState.OPEN),
        Task(id=4, text="Open fourth", state=TaskState.OPEN),
    ]
    assert initial_selection(tasks) == 3


def test_falls_back_to_first_migrated_when_no_open_task_exists() -> None:
    tasks = [
        Task(id=1, text="Deleted first", state=TaskState.DELETED),
        Task(id=2, text="Migrated second", state=TaskState.MIGRATED),
        Task(id=3, text="Completed third", state=TaskState.COMPLETED),
    ]
    assert initial_selection(tasks) == 2


def test_falls_back_to_first_completed_when_no_open_or_migrated_task_exists() -> None:
    tasks = [
        Task(id=1, text="Deleted first", state=TaskState.DELETED),
        Task(id=2, text="Completed second", state=TaskState.COMPLETED),
    ]
    assert initial_selection(tasks) == 2


def test_falls_back_to_first_deleted_when_only_deleted_tasks_exist() -> None:
    tasks = [
        Task(id=1, text="Deleted first", state=TaskState.DELETED),
        Task(id=2, text="Deleted second", state=TaskState.DELETED),
    ]
    assert initial_selection(tasks) == 1

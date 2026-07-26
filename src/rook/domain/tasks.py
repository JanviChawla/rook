from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class TaskState(str, Enum):
    OPEN = "open"
    MIGRATED = "migrated"
    COMPLETED = "completed"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class Task:
    """A one-line Task and its current persistent state.

    This is intentionally minimal for Phase 2 (id, text, state only).
    Ordering and timestamps are added when a phase first needs them.
    """

    id: int
    text: str
    state: TaskState


# Section 6.2: initial selection prefers the first Open Task, then the
# first Migrated, then the first Completed, then the first Soft-Deleted.
_INITIAL_SELECTION_PRIORITY = (
    TaskState.OPEN,
    TaskState.MIGRATED,
    TaskState.COMPLETED,
    TaskState.DELETED,
)


def initial_selection(tasks: Sequence[Task]) -> int | None:
    """The id of the Task that should be selected when Today first opens.

    Returns None when there are no Tasks to select.
    """
    for state in _INITIAL_SELECTION_PRIORITY:
        for task in tasks:
            if task.state is state:
                return task.id
    return None

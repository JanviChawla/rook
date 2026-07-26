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

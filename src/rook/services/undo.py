from dataclasses import dataclass

from rook.domain.tasks import TaskState
from rook.persistence.tasks import TaskSnapshot


@dataclass(frozen=True, slots=True)
class DeleteCreatedTask:
    """Undo a Task creation: the Task is Open and untouched since single-
    level undo guarantees nothing else has mutated it since (Section 15.19).
    """

    task_id: int


@dataclass(frozen=True, slots=True)
class RestoreTaskText:
    """Undo a text edit."""

    task_id: int
    text: str


@dataclass(frozen=True, slots=True)
class RestoreTaskState:
    """Undo a state change (`x`, `>`, or a first `d`)."""

    task_id: int
    state: TaskState


@dataclass(frozen=True, slots=True)
class RestoreTaskSnapshot:
    """Undo a permanent removal (second `d`), reinserting at its original
    list position."""

    index: int
    snapshot: TaskSnapshot


UndoCommand = DeleteCreatedTask | RestoreTaskText | RestoreTaskState | RestoreTaskSnapshot


class UndoManager:
    """Holds at most one inverse command for the current session (Section
    16.20). Pure in-memory bookkeeping - no database connection, no
    widgets, no asyncio. The presentation layer decides how to apply each
    command type and through which service calls.
    """

    def __init__(self) -> None:
        self._command: UndoCommand | None = None

    def record(self, command: UndoCommand) -> None:
        self._command = command

    def clear(self) -> None:
        self._command = None

    @property
    def has_undo(self) -> bool:
        return self._command is not None

    def take(self) -> UndoCommand | None:
        """Remove and return the pending command, if any.

        Version 1 has no redo, so taking a command always clears the slot
        - if applying it fails, the caller may choose to record() it again.
        """
        command = self._command
        self._command = None
        return command

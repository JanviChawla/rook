import sqlite3
from collections.abc import Callable
from datetime import date, datetime

from rook.domain.tasks import Task, TaskState
from rook.persistence.tasks import TaskRepository


class PersistenceError(Exception):
    """Raised when a Task mutation could not be durably saved.

    The presentation layer catches this and shows a status message
    (Section 10.16) rather than pretending the mutation succeeded
    (FR-104).
    """


class TaskService:
    """Coordinates Task mutations for the presentation layer.

    Translates low-level sqlite3 failures into PersistenceError so
    widgets never need to know about sqlite3 directly.
    """

    def __init__(
        self,
        repository: TaskRepository,
        *,
        now_provider: Callable[[], datetime] = datetime.now,
        today_provider: Callable[[], date] = date.today,
    ) -> None:
        self._repository = repository
        self._now_provider = now_provider
        self._today_provider = today_provider

    def list_active_tasks(self) -> list[Task]:
        try:
            return self._repository.list_active_tasks()
        except sqlite3.Error as error:
            raise PersistenceError(str(error)) from error

    def create_task(self, text: str) -> Task:
        try:
            return self._repository.create_task(
                text, now=self._now_provider(), local_date=self._today_provider()
            )
        except sqlite3.Error as error:
            raise PersistenceError(str(error)) from error

    def update_task_text(self, task_id: int, text: str) -> Task:
        try:
            return self._repository.update_task_text(task_id, text, now=self._now_provider())
        except sqlite3.Error as error:
            raise PersistenceError(str(error)) from error

    def set_task_state(self, task_id: int, state: TaskState) -> Task:
        try:
            return self._repository.set_task_state(
                task_id, state, now=self._now_provider(), local_date=self._today_provider()
            )
        except sqlite3.Error as error:
            raise PersistenceError(str(error)) from error

    def delete_task(self, task_id: int) -> Task:
        """Permanently remove a Soft-Deleted Task, returning its last
        known data so a future undo (Phase 7) can restore it."""
        try:
            return self._repository.delete_active_task(task_id)
        except sqlite3.Error as error:
            raise PersistenceError(str(error)) from error

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from rook.domain.tasks import Task, initial_selection
from rook.widgets.task_row import TaskRow

EMPTY_TODAY_MESSAGE = "No tasks yet. Press n to write the first one."


class TaskListView(VerticalScroll):
    """Today's scrollable task list with a single bounded selection cursor.

    Selection is tracked by Task id rather than row index (Section 21.8),
    so it stays meaningful if the underlying task order ever changes.
    """

    def __init__(
        self,
        tasks: Sequence[Task],
        *,
        safe_symbols: bool = False,
        id: str | None = None,
    ) -> None:
        # can_focus=False: ScrollableContainer is focusable and binds
        # up/down to its own scroll_up/scroll_down actions (inherited
        # bindings can't be cleared by overriding BINDINGS in a subclass -
        # Textual's binding resolution merges the whole class hierarchy).
        # Once this container is scrollable, that would swallow the key
        # before it ever reaches RookApp's selection bindings. Scrolling
        # here must be a side effect of moving the selection (Section
        # 6.4), not an independent action, so this widget never takes
        # focus and arrow keys go straight to the App.
        super().__init__(id=id, can_focus=False)
        self._tasks = list(tasks)
        self._safe_symbols = safe_symbols
        self.selected_task_id: int | None = initial_selection(self._tasks)

    def compose(self) -> ComposeResult:
        if not self._tasks:
            yield Static(f"  {EMPTY_TODAY_MESSAGE}", markup=False)
            return

        for task in self._tasks:
            yield TaskRow(
                task,
                selected=(task.id == self.selected_task_id),
                safe_symbols=self._safe_symbols,
                id=f"task-row-{task.id}",
            )

    def select_previous(self) -> None:
        self._move_selection(-1)

    def select_next(self) -> None:
        self._move_selection(1)

    def _move_selection(self, delta: int) -> None:
        index = self._index_of_selected()
        if index is None:
            return

        new_index = max(0, min(len(self._tasks) - 1, index + delta))
        if new_index == index:
            return

        self.selected_task_id = self._tasks[new_index].id
        self._apply_selection()

    def _index_of_selected(self) -> int | None:
        for index, task in enumerate(self._tasks):
            if task.id == self.selected_task_id:
                return index
        return None

    def _apply_selection(self) -> None:
        for row in self.query(TaskRow):
            row.set_selected(row.item.id == self.selected_task_id)
            if row.selected:
                row.scroll_visible(animate=False)

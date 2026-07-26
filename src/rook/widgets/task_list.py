import dataclasses
from collections.abc import Sequence
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Input, Static

from rook.domain.tasks import Task, TaskState, initial_selection
from rook.widgets.task_line_input import TaskLineInput
from rook.widgets.task_row import TaskRow

EMPTY_TODAY_MESSAGE = "No tasks yet. Press n to write the first one."


class TaskListView(VerticalScroll):
    """Today's scrollable task list with a single bounded selection cursor.

    Selection is tracked by Task id rather than row index (Section 21.8),
    so it stays meaningful if the underlying task order ever changes.
    """

    # This container itself never takes focus (see can_focus=False below),
    # but a binding declared here still applies while a descendant (the
    # TaskLineInput being edited) has focus, because Textual's binding
    # resolution walks up the full ancestor chain from the focused widget.
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel_edit", "Cancel", show=False),
    ]

    class StatusMessage(Message):
        """A one-line status hint for the App to display (Section 10.16)."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    class EditingChanged(Message):
        """Whether a Task row is currently being created or edited."""

        def __init__(self, editing: bool) -> None:
            self.editing = editing
            super().__init__()

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
        self._editing_task_id: int | None = None
        self._creating = False
        self._pending_edit_value = ""
        self._pre_edit_selected_task_id: int | None = None

    def compose(self) -> ComposeResult:
        if not self._tasks:
            yield Static(f"  {EMPTY_TODAY_MESSAGE}", markup=False)
            return

        for task in self._tasks:
            is_editing_this = task.id == self._editing_task_id
            yield TaskRow(
                task,
                selected=(task.id == self.selected_task_id),
                safe_symbols=self._safe_symbols,
                editing=is_editing_this,
                edit_value=self._pending_edit_value if is_editing_this else "",
                id=f"task-row-{task.id}",
            )

    # --- Navigation (Phase 3) -------------------------------------------

    def select_previous(self) -> None:
        if self._editing_task_id is not None:
            return
        self._move_selection(-1)

    def select_next(self) -> None:
        if self._editing_task_id is not None:
            return
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

    # --- Creation and editing (Phase 4) ----------------------------------

    async def begin_create(self) -> None:
        if self._editing_task_id is not None:
            return

        self._pre_edit_selected_task_id = self.selected_task_id
        new_id = max((task.id for task in self._tasks), default=0) + 1
        self._tasks.append(Task(id=new_id, text="", state=TaskState.OPEN))
        self.selected_task_id = new_id
        self._editing_task_id = new_id
        self._creating = True
        self._pending_edit_value = ""
        self.post_message(self.EditingChanged(True))
        await self.recompose()

    async def begin_edit(self) -> None:
        if self._editing_task_id is not None:
            return

        index = self._index_of_selected()
        if index is None:
            return

        task = self._tasks[index]
        self._editing_task_id = task.id
        self._creating = False
        self._pending_edit_value = task.text
        self.post_message(self.EditingChanged(True))
        await self.recompose()

    async def action_cancel_edit(self) -> None:
        if self._editing_task_id is None:
            return
        if self._creating:
            await self._cancel_creation()
        else:
            await self._exit_editing()

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        message.stop()
        if self._editing_task_id is None:
            return

        is_blank = message.value.strip() == ""

        if self._creating:
            if is_blank:
                await self._cancel_creation()
            else:
                await self._commit_edit(message.value)
        elif is_blank:
            self.post_message(self.StatusMessage("Task cannot be blank."))
        else:
            await self._commit_edit(message.value)

    async def on_task_line_input_empty_backspace(
        self, message: TaskLineInput.EmptyBackspace
    ) -> None:
        message.stop()
        # Section 9.5: Backspace on an already-empty *existing* Task edit
        # must not delete or exit. Only a brand new, unsaved Task cancels.
        if self._creating:
            await self._cancel_creation()

    async def _commit_edit(self, value: str) -> None:
        for index, task in enumerate(self._tasks):
            if task.id == self._editing_task_id:
                self._tasks[index] = dataclasses.replace(task, text=value)
                break
        await self._exit_editing()

    async def _cancel_creation(self) -> None:
        self._tasks = [task for task in self._tasks if task.id != self._editing_task_id]
        self.selected_task_id = self._pre_edit_selected_task_id
        await self._exit_editing()

    async def _exit_editing(self) -> None:
        self._editing_task_id = None
        self._creating = False
        self._pending_edit_value = ""
        self.post_message(self.EditingChanged(False))
        await self.recompose()

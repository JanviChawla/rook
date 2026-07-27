import textwrap

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from rook.domain.tasks import Task, TaskState
from rook.symbols import PREFERRED, PREFIX_WIDTH, SAFE, state_symbol
from rook.widgets.task_line_input import TaskLineInput


def render_task_row_text(task: Task, *, selected: bool, width: int, safe_symbols: bool) -> Text:
    """Build one Task row as a Rich Text.

    Continuation lines of a wrapped Task align under the text rather than
    repeating the selection or state-symbol columns (Section 11.3). A
    Deleted Task keeps its normal bullet with strikethrough styling in the
    preferred mode, or the ``~`` fallback symbol with muted styling when
    ``safe_symbols`` is set (Section 11.5, 11.7). The selection column
    shows the accent-styled cursor only on the selected row (Section 11.6).
    """
    symbols = SAFE if safe_symbols else PREFERRED
    body_width = max(width - PREFIX_WIDTH, 1)

    symbol = state_symbol(task.state, symbols, safe_mode=safe_symbols)
    cursor = symbols.selected if selected else " "
    prefix = f"{cursor} {symbol} "
    wrapped_lines = textwrap.wrap(
        task.text,
        width=body_width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]

    row = Text(prefix + wrapped_lines[0])
    for continuation in wrapped_lines[1:]:
        row.append("\n" + " " * PREFIX_WIDTH + continuation)

    if task.state is TaskState.DELETED and not safe_symbols:
        row.stylize("strike", len(prefix))

    if selected:
        row.stylize("bold", 0, 1)

    return row


class TaskRow(Widget):
    """One Task row within the scrollable Today task list.

    Normally renders as read-only text via ``render_task_row_text``
    (unchanged from Phase 2/3). While ``editing`` is True, it instead
    composes a small prefix plus a live ``TaskLineInput`` in place of
    that text - creation and editing happen directly on the row, never
    in a separate dialog (Section 2.5).
    """

    DEFAULT_CSS = """
    TaskRow {
        height: auto;
    }
    TaskRow.-resolved {
        opacity: 0.5;
    }
    TaskRow.-resolved.-editing {
        opacity: 1.0;
    }
    TaskRow.-editing {
        layout: horizontal;
        height: 1;
    }
    TaskRow.-editing .task-row-prefix {
        width: 4;
        height: 1;
    }
    TaskRow.-editing TaskLineInput {
        width: 1fr;
        height: 1;
    }
    """

    def __init__(
        self,
        item: Task,
        *,
        selected: bool = False,
        safe_symbols: bool = False,
        editing: bool = False,
        edit_value: str = "",
        id: str | None = None,
    ) -> None:
        # Note: "item" (not "task") because Widget already reserves the
        # read-only "task" property for its own backing asyncio Task.
        super().__init__(id=id)
        self.item = item
        self.selected = selected
        self._safe_symbols = safe_symbols
        self.editing = editing
        self._edit_value = edit_value
        if editing:
            self.add_class("-editing")
        if item.state is not TaskState.OPEN:
            self.add_class("-resolved")

    def compose(self) -> ComposeResult:
        if self.editing:
            symbols = SAFE if self._safe_symbols else PREFERRED
            cursor = symbols.selected if self.selected else " "
            symbol = state_symbol(self.item.state, symbols, safe_mode=self._safe_symbols)
            # markup=False: the prefix is fixed chrome, never user text.
            yield Static(f"{cursor} {symbol} ", classes="task-row-prefix", markup=False)
            yield TaskLineInput(
                self._edit_value,
                compact=True,
                select_on_focus=False,
                max_length=1000,
            )
        else:
            # markup=False: Task text must never be interpreted as Rich
            # console markup, so a task literally containing "[bold]"
            # renders unchanged.
            yield Static(markup=False)

    def on_mount(self) -> None:
        if self.editing:
            editor = self.query_one(TaskLineInput)
            editor.cursor_position = len(editor.value)
            editor.focus()
        else:
            self._refresh_display()

    def on_resize(self, event: events.Resize) -> None:
        if not self.editing:
            self._refresh_display()

    def set_selected(self, selected: bool) -> None:
        if self.selected != selected:
            self.selected = selected
            if not self.editing:
                self._refresh_display()

    def set_item(self, item: Task) -> None:
        """Redraw after the underlying Task's state or text changed
        (Section 8), without needing the whole list to recompose."""
        self.item = item
        if item.state is TaskState.OPEN:
            self.remove_class("-resolved")
        else:
            self.add_class("-resolved")
        if not self.editing:
            self._refresh_display()

    def _refresh_display(self) -> None:
        width = self.size.width or 80
        display = self.query_one(Static)
        display.update(
            render_task_row_text(
                self.item,
                selected=self.selected,
                width=width,
                safe_symbols=self._safe_symbols,
            )
        )

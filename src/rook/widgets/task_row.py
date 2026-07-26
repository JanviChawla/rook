import textwrap

from rich.text import Text
from textual import events
from textual.widgets import Static

from rook.domain.tasks import Task, TaskState
from rook.symbols import PREFERRED, PREFIX_WIDTH, SAFE, state_symbol


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

    if task.state is TaskState.DELETED:
        if safe_symbols:
            row.stylize("dim")
        else:
            row.stylize("strike", len(prefix))

    if selected:
        row.stylize("bold", 0, 1)

    return row


class TaskRow(Static):
    """One Task row within the scrollable Today task list."""

    def __init__(
        self,
        item: Task,
        *,
        selected: bool = False,
        safe_symbols: bool = False,
        id: str | None = None,
    ) -> None:
        # markup=False: Task text must never be interpreted as Rich console
        # markup, so a task literally containing "[bold]" renders unchanged.
        # Note: "item" (not "task") because Widget already reserves the
        # read-only "task" property for its own backing asyncio Task.
        super().__init__(id=id, markup=False)
        self.item = item
        self.selected = selected
        self._safe_symbols = safe_symbols

    def on_mount(self) -> None:
        self._refresh_content()

    def on_resize(self, event: events.Resize) -> None:
        self._refresh_content()

    def set_selected(self, selected: bool) -> None:
        if self.selected != selected:
            self.selected = selected
            self._refresh_content()

    def _refresh_content(self) -> None:
        width = self.size.width or 80
        self.update(
            render_task_row_text(
                self.item,
                selected=self.selected,
                width=width,
                safe_symbols=self._safe_symbols,
            )
        )

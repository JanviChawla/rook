import textwrap
from collections.abc import Sequence

from rich.text import Text
from textual import events
from textual.widgets import Static

from rook.domain.tasks import Task, TaskState
from rook.symbols import PREFERRED, PREFIX_WIDTH, SAFE, state_symbol

EMPTY_TODAY_MESSAGE = "No tasks yet. Press n to write the first one."


def render_task_lines(tasks: Sequence[Task], *, width: int, safe_symbols: bool) -> Text:
    """Build the Today task list as a single multi-line Rich Text.

    Continuation lines of a wrapped Task align under the text rather than
    repeating the selection or state-symbol columns (Section 11.3). A
    Deleted Task keeps its normal bullet with strikethrough styling in the
    preferred mode, or the ``~`` fallback symbol with muted styling when
    ``safe_symbols`` is set (Section 11.5, 11.7).
    """
    if not tasks:
        return Text(f"  {EMPTY_TODAY_MESSAGE}")

    symbols = SAFE if safe_symbols else PREFERRED
    body_width = max(width - PREFIX_WIDTH, 1)
    rows: list[Text] = []

    for task in tasks:
        symbol = state_symbol(task.state, symbols, safe_mode=safe_symbols)
        prefix = f"  {symbol} "
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

        rows.append(row)

    return Text("\n").join(rows)


class TaskListView(Static):
    """Renders Today's task list from in-memory Task-like data.

    Phase 2 has no selection, mutation, or persistence; the selection
    column is reserved but always blank.
    """

    def __init__(
        self,
        tasks: Sequence[Task],
        *,
        safe_symbols: bool = False,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._tasks = list(tasks)
        self._safe_symbols = safe_symbols

    def on_mount(self) -> None:
        self._refresh_content()

    def on_resize(self, event: events.Resize) -> None:
        self._refresh_content()

    def _refresh_content(self) -> None:
        width = self.size.width or 80
        self.update(render_task_lines(self._tasks, width=width, safe_symbols=self._safe_symbols))

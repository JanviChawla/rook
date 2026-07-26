from collections.abc import Callable, Sequence
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from rook import branding
from rook.domain.tasks import Task, TaskState
from rook.formatting import format_header_date
from rook.widgets.shortcut_footer import ShortcutFooter
from rook.widgets.task_list import TaskListView

TodayProvider = Callable[[], date]

# Hardcoded fictional display data for Phase 2 (Section 19.20 test-data
# policy). Persistence arrives in Phase 5; this list is not user-editable.
SAMPLE_TASKS: list[Task] = [
    Task(id=1, text="Finish the client deck", state=TaskState.OPEN),
    Task(id=2, text="Read Chapter 3", state=TaskState.MIGRATED),
    Task(id=3, text="Submit the expense report", state=TaskState.COMPLETED),
    Task(id=4, text="Buy another monitor", state=TaskState.DELETED),
    Task(
        id=5,
        text=(
            "Draft the long-form article explaining the design decisions "
            "behind the terminal journal and its intentionally limited scope"
        ),
        state=TaskState.OPEN,
    ),
]


class RookApp(App[None]):
    """The Rook terminal shell.

    Phase 2 renders a hardcoded Today task list. There is no selection,
    mutation, or persistence yet.
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #header, #mascot-quote, #spacer {
        height: 1;
    }

    #task-list {
        height: 1fr;
    }

    #footer {
        height: 1;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        today_provider: TodayProvider = date.today,
        *,
        tasks: Sequence[Task] | None = None,
        safe_symbols: bool = False,
    ) -> None:
        super().__init__()
        self._today_provider = today_provider
        self._tasks = list(SAMPLE_TASKS if tasks is None else tasks)
        self._safe_symbols = safe_symbols
        # Map foreground/background to the terminal's own ANSI defaults
        # instead of Textual's fixed truecolor theme, so the app respects
        # the user's existing terminal background (Section 11.9-11.10).
        self.theme = "ansi-dark"

    def compose(self) -> ComposeResult:
        today = self._today_provider()
        header_text = f"{branding.DISPLAY_NAME} {branding.ICON}  {format_header_date(today)}"
        mascot_quote_text = f'{branding.MASCOT}  "{branding.QUOTE}"'

        yield Static(header_text, id="header", markup=False)
        yield Static(mascot_quote_text, id="mascot-quote", markup=False)
        yield Static("", id="spacer")
        yield TaskListView(self._tasks, safe_symbols=self._safe_symbols, id="task-list")
        yield ShortcutFooter(has_tasks=bool(self._tasks), id="footer")

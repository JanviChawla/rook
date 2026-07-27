from collections.abc import Callable
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from rook import branding
from rook.formatting import format_header_date
from rook.services.tasks import TaskService
from rook.widgets.shortcut_footer import ShortcutFooter
from rook.widgets.task_list import TaskListView

TodayProvider = Callable[[], date]


class RookApp(App[None]):
    """The Rook terminal shell.

    Phase 5 replaces the in-memory Task list with SQLite as the source of
    truth, via an injected TaskService. Task state changes, Archive, and
    Routines are still not implemented.
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #header, #mascot-quote, #spacer, #status {
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
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("n", "new_task", "New", show=False),
        Binding("e", "edit_task", "Edit", show=False),
    ]

    def __init__(
        self,
        today_provider: TodayProvider = date.today,
        *,
        task_service: TaskService,
        safe_symbols: bool = False,
    ) -> None:
        super().__init__()
        self._today_provider = today_provider
        self._task_service = task_service
        self._safe_symbols = safe_symbols
        # Map foreground/background to the terminal's own ANSI defaults
        # instead of Textual's fixed truecolor theme, so the app respects
        # the user's existing terminal background (Section 11.9-11.10).
        self.theme = "ansi-dark"

    def compose(self) -> ComposeResult:
        today = self._today_provider()
        header_text = f"{branding.DISPLAY_NAME} {branding.ICON}  {format_header_date(today)}"
        mascot_quote_text = f'{branding.MASCOT}  "{branding.QUOTE}"'
        tasks = self._task_service.list_active_tasks()

        yield Static(header_text, id="header", markup=False)
        yield Static(mascot_quote_text, id="mascot-quote", markup=False)
        yield Static("", id="spacer")
        yield TaskListView(
            tasks, task_service=self._task_service, safe_symbols=self._safe_symbols, id="task-list"
        )
        yield Static("", id="status", markup=False)
        yield ShortcutFooter(has_tasks=bool(tasks), id="footer")

    def action_cursor_up(self) -> None:
        self.query_one(TaskListView).select_previous()

    def action_cursor_down(self) -> None:
        self.query_one(TaskListView).select_next()

    async def action_new_task(self) -> None:
        await self.query_one(TaskListView).begin_create()

    async def action_edit_task(self) -> None:
        await self.query_one(TaskListView).begin_edit()

    def on_task_list_view_status_message(self, message: TaskListView.StatusMessage) -> None:
        self.query_one("#status", Static).update(message.text)

    def on_task_list_view_editing_changed(self, message: TaskListView.EditingChanged) -> None:
        self.query_one(ShortcutFooter).set_editing(message.editing)
        self.query_one("#status", Static).update("")

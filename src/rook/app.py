from collections.abc import Callable
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from rook import branding
from rook.formatting import format_header_date
from rook.services.tasks import TaskService
from rook.services.undo import UndoManager
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

    #header {
        text-style: bold;
    }

    #task-list {
        height: 1fr;
        /* The "ansi-dark" theme doesn't define scrollbar variables (only
         * "ansi-light" happens to), so these fall back to Textual's fixed
         * truecolor defaults - the mismatched, chunky bar reported after
         * scrolling a long list. Set them directly to ANSI colors instead,
         * and use a slimmer single-column bar (Section 11.1 "compact"). */
        scrollbar-size-vertical: 1;
        scrollbar-color: ansi_default;
        scrollbar-color-hover: ansi_default;
        scrollbar-color-active: ansi_default;
        scrollbar-background: ansi_default;
        scrollbar-background-hover: ansi_default;
        scrollbar-background-active: ansi_default;
        scrollbar-corner-color: ansi_default;
    }

    /* "ansi-dark" hardcodes the text-entry cursor to a solid reverse-video
     * block in ansi_black on ansi_bright_white, which many customized
     * terminal palettes remap to something unrelated to the terminal's
     * actual foreground/background (reported as an unrelated light gray).
     * Reversing the terminal's own default foreground instead keeps the
     * filled-block look but in the user's own theme color. This is Rook's
     * own simulated text cursor, not the terminal's hardware cursor - a
     * full-screen app owning the whole display can't repurpose the
     * terminal's native caret for a styled, multi-character-wide input. */
    TaskLineInput > .input--cursor {
        color: ansi_default;
        text-style: reverse;
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
        Binding("enter", "edit_task", "Edit", show=False),
        Binding("x", "toggle_completed", "Complete", show=False),
        Binding(">", "toggle_migrated", "Migrate", show=False),
        Binding("d", "delete_or_remove", "Delete", show=False),
        Binding("u", "undo", "Undo", show=False),
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
        # Session-scoped: owned here (not per-widget) so a later Routine
        # phase can share the same single undo slot (Section 6.10).
        self._undo_manager = UndoManager()
        self._safe_symbols = safe_symbols
        # Map foreground/background to the terminal's own ANSI defaults
        # instead of Textual's fixed truecolor theme, so the app respects
        # the user's existing terminal background (Section 11.9-11.10).
        self.theme = "ansi-dark"

    def compose(self) -> ComposeResult:
        today = self._today_provider()
        header_text = (
            f"{branding.DISPLAY_NAME.lower()} {branding.ICON}  {format_header_date(today)}"
        )
        mascot_quote_text = f'{branding.MASCOT}  "{branding.QUOTE}"'
        tasks = self._task_service.list_active_tasks()

        yield Static(header_text, id="header", markup=False)
        yield Static(mascot_quote_text, id="mascot-quote", markup=False)
        yield Static("", id="spacer")
        yield TaskListView(
            tasks,
            task_service=self._task_service,
            undo_manager=self._undo_manager,
            safe_symbols=self._safe_symbols,
            id="task-list",
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

    async def action_toggle_completed(self) -> None:
        await self.query_one(TaskListView).toggle_completed()

    async def action_toggle_migrated(self) -> None:
        await self.query_one(TaskListView).toggle_migrated()

    async def action_delete_or_remove(self) -> None:
        await self.query_one(TaskListView).delete_or_remove()

    async def action_undo(self) -> None:
        await self.query_one(TaskListView).undo()

    def on_task_list_view_status_message(self, message: TaskListView.StatusMessage) -> None:
        self.query_one("#status", Static).update(message.text)

    def on_task_list_view_editing_changed(self, message: TaskListView.EditingChanged) -> None:
        self.query_one(ShortcutFooter).set_editing(message.editing)
        self.query_one("#status", Static).update("")

    def on_task_list_view_tasks_empty_changed(
        self, message: TaskListView.TasksEmptyChanged
    ) -> None:
        self.query_one(ShortcutFooter).set_has_tasks(message.has_tasks)

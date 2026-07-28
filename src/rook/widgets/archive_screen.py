import sqlite3
from datetime import date, timedelta

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from rook import branding
from rook.domain.tasks import TaskState
from rook.persistence.archive import ArchiveRepository, week_start_for


def _format_week_range(week_start: date) -> str:
    week_end = week_start + timedelta(days=6)
    if week_start.year == week_end.year:
        if week_start.month == week_end.month:
            return f"{week_start:%B} {week_start.day}–{week_end.day}, {week_start:%Y}"
        return f"{week_start:%B} {week_start.day}–{week_end:%B} {week_end.day}, {week_start:%Y}"
    return (
        f"{week_start:%B} {week_start.day}, {week_start:%Y}"
        f"–{week_end:%B} {week_end.day}, {week_end:%Y}"
    )


class ArchiveScreen(Screen[None]):
    """Read-only weekly archive view (Section 21.14)."""

    BINDINGS = [
        Binding("escape", "go_today", "Today", show=False),
        Binding("q", "go_today", "Today", show=False),
        Binding("left", "prev_week", "Older", show=False),
        Binding("right", "next_week", "Newer", show=False),
    ]

    CSS = """
    ArchiveScreen {
        layout: vertical;
    }

    ArchiveScreen #archive-header {
        height: 1;
        text-style: bold;
    }

    ArchiveScreen #archive-spacer {
        height: 1;
    }

    ArchiveScreen #archive-scroll {
        height: 1fr;
        scrollbar-size-vertical: 1;
        scrollbar-color: ansi_default;
        scrollbar-color-hover: ansi_default;
        scrollbar-color-active: ansi_default;
        scrollbar-background: ansi_default;
        scrollbar-background-hover: ansi_default;
        scrollbar-background-active: ansi_default;
        scrollbar-corner-color: ansi_default;
    }

    ArchiveScreen #archive-footer {
        height: 1;
        dock: bottom;
    }
    """

    def __init__(self, *, connection: sqlite3.Connection, first_weekday: int) -> None:
        super().__init__()
        self._repo = ArchiveRepository(connection)
        self._first_weekday = first_weekday
        self._all_dates: list[date] = []
        self._current_week_start: date | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="archive-header", markup=False)
        yield Static("", id="archive-spacer")
        yield VerticalScroll(
            Static("", id="archive-content"),
            id="archive-scroll",
        )
        yield Static("", id="archive-footer", markup=False)

    def on_mount(self) -> None:
        self._all_dates = self._repo.list_archive_dates()
        if self._all_dates:
            self._current_week_start = week_start_for(
                self._all_dates[0], first_weekday=self._first_weekday
            )
        self._refresh_view()

    def _refresh_view(self) -> None:
        self._update_header()
        self._update_content()
        self._update_footer()

    def _update_header(self) -> None:
        header = self.query_one("#archive-header", Static)
        if self._current_week_start is None:
            header.update(f"{branding.DISPLAY_NAME.lower()} {branding.ICON}  Archive")
        else:
            week_range = _format_week_range(self._current_week_start)
            header.update(
                f"{branding.DISPLAY_NAME.lower()} {branding.ICON}  Archive — {week_range}"
            )

    def _update_content(self) -> None:
        content = self.query_one("#archive-content", Static)
        if self._current_week_start is None:
            content.update("No archived tasks yet.")
            return

        week_end = self._current_week_start + timedelta(days=7)
        days = self._repo.list_week_items(self._current_week_start, week_end)
        if not days:
            content.update("No tasks archived this week.")
            return

        lines: list[str] = []
        for i, (day, tasks) in enumerate(days):
            if i > 0:
                lines.append("")
            lines.append(f"[bold]{day:%A, %B} {day.day}[/bold]")
            for task in tasks:
                safe_text = escape(task.text)
                if task.state == TaskState.COMPLETED:
                    lines.append(f"  × {safe_text}")
                else:
                    lines.append(f"  [strike]• {safe_text}[/strike]")
        content.update("\n".join(lines))

    def _update_footer(self) -> None:
        footer = self.query_one("#archive-footer", Static)
        parts: list[str] = []
        if self._has_older_week():
            parts.append("[←] older")
        if self._has_newer_week():
            parts.append("[→] newer")
        parts.append("[Esc] today")
        footer.update("   ".join(parts))

    def _has_older_week(self) -> bool:
        if not self._all_dates or self._current_week_start is None:
            return False
        return self._all_dates[-1] < self._current_week_start

    def _has_newer_week(self) -> bool:
        if not self._all_dates or self._current_week_start is None:
            return False
        return self._all_dates[0] >= self._current_week_start + timedelta(days=7)

    def action_go_today(self) -> None:
        self.app.pop_screen()

    def action_prev_week(self) -> None:
        if not self._has_older_week():
            return
        target = next(d for d in self._all_dates if d < self._current_week_start)
        self._current_week_start = week_start_for(target, first_weekday=self._first_weekday)
        self._refresh_view()

    def action_next_week(self) -> None:
        if not self._has_newer_week():
            return
        next_start = self._current_week_start + timedelta(days=7)
        target = next(d for d in reversed(self._all_dates) if d >= next_start)
        self._current_week_start = week_start_for(target, first_weekday=self._first_weekday)
        self._refresh_view()

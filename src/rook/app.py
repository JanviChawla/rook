from collections.abc import Callable
from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from rook import branding
from rook.formatting import format_header_date

TodayProvider = Callable[[], date]


class RookApp(App[None]):
    """The Rook terminal shell.

    Phase 1 renders only the static header, mascot/quote line, and
    footer. There is no Task list, persistence, or Task interaction yet.
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #header, #mascot-quote, #spacer {
        height: 1;
    }

    #footer {
        height: 1;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, today_provider: TodayProvider = date.today) -> None:
        super().__init__()
        self._today_provider = today_provider
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
        yield Static("[q] quit", id="footer", markup=False)

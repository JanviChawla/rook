import asyncio
from datetime import date

from textual.widgets import Static

from rook import branding
from rook.app import RookApp
from rook.formatting import format_header_date

FIXED_DATE = date(2026, 7, 24)


def _fixed_today() -> date:
    return FIXED_DATE


def test_today_screen_renders_header_mascot_and_footer() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test() as pilot:
            header = pilot.app.query_one("#header", Static)
            mascot_quote = pilot.app.query_one("#mascot-quote", Static)
            footer = pilot.app.query_one("#footer", Static)

            expected_header = (
                f"{branding.DISPLAY_NAME} {branding.ICON}  {format_header_date(FIXED_DATE)}"
            )
            expected_mascot_quote = f'{branding.MASCOT}  "{branding.QUOTE}"'

            assert str(header.content) == expected_header
            assert str(mascot_quote.content) == expected_mascot_quote
            assert str(footer.content) == "[q] quit"

    asyncio.run(scenario())


def test_uses_terminal_native_background_and_foreground() -> None:
    """The app must respect the user's existing terminal background
    (Section 11.9-11.10, D-020) rather than force Textual's fixed theme."""

    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test():
            assert app.theme == "ansi-dark"
            theme = app.get_theme(app.theme)
            assert theme is not None
            assert theme.background == "ansi_default"
            assert theme.foreground == "ansi_default"

    asyncio.run(scenario())


def test_pressing_q_quits() -> None:
    async def scenario() -> None:
        app = RookApp(today_provider=_fixed_today)
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert app.return_code == 0

    asyncio.run(scenario())

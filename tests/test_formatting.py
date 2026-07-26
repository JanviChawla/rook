from datetime import date

from rook.formatting import format_header_date


def test_format_header_date_two_digit_day() -> None:
    assert format_header_date(date(2026, 7, 24)) == "Friday, July 24, 2026"


def test_format_header_date_single_digit_day_has_no_leading_zero() -> None:
    assert format_header_date(date(2026, 7, 4)) == "Saturday, July 4, 2026"

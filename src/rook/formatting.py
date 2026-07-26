from datetime import date


def format_header_date(today: date) -> str:
    """Render a date as "Weekday, Month D, Year" without a leading zero.

    ``strftime("%-d")`` is a glibc extension not available on Windows'
    CRT, so the day number is formatted separately instead.
    """
    return f"{today:%A, %B} {today.day}, {today:%Y}"

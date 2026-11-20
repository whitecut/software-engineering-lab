"""Shared helpers: dates, money and time formatting."""

from __future__ import annotations

from datetime import date, datetime, timedelta

DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def today() -> date:
    """Return the current local date."""
    return date.today()


def now_text() -> str:
    """Return the current timestamp as text."""
    return datetime.now().strftime(TIME_FMT)


def parse_date(value: str) -> date:
    """Parse an ISO date string (YYYY-MM-DD)."""
    return datetime.strptime(value.strip(), DATE_FMT).date()


def fmt_date(value: date) -> str:
    """Format a date as YYYY-MM-DD."""
    return value.strftime(DATE_FMT)


def date_range(start: date, end: date) -> list[date]:
    """Return all dates in [start, end), used for hotel nights."""
    days: list[date] = []
    cursor = start
    while cursor < end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def money(value: float) -> str:
    """Format an amount with two decimals."""
    return f"{value:,.2f}"


def nights(start: date, end: date) -> int:
    """Number of nights between two dates."""
    return (end - start).days

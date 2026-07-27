"""
PayPal Shared Utilities

Helpers shared across the PayPal CLI utilities.
"""

from datetime import datetime, timedelta

import click

_DATE_FORMAT = "%Y-%m-%d"


def _parse_day(value, option):
    """Parse a YYYY-MM-DD CLI value, raising a clear error on bad input."""
    try:
        return datetime.strptime(value, _DATE_FORMAT)
    except ValueError as exc:
        raise click.BadParameter(
            f"{option} must be in YYYY-MM-DD format, got '{value}'"
        ) from exc


def parse_date_range(start=None, end=None, days=30):
    """
    Build an ISO-8601 date range for the PayPal reporting APIs.

    The range always covers whole days: it starts at 00:00:00 on the start date
    and ends at 23:59:59 on the end date.

    Args:
        start (str): Start date as YYYY-MM-DD. When ``None``, defaults to
            ``days`` before the end date.
        end (str): End date as YYYY-MM-DD. When ``None``, defaults to the
            current UTC date.
        days (int): Number of days to look back when ``start`` is ``None``.

    Returns:
        tuple: (start_str, end_str) as YYYY-MM-DDTHH:MM:SSZ strings.

    Raises:
        click.BadParameter: If a date is not YYYY-MM-DD or ``days`` is negative.

    Examples:
        >>> parse_date_range(start="2024-01-01", end="2024-01-31")
        ('2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z')
    """
    if days < 0:
        raise click.BadParameter(f"days must be zero or greater, got {days}")

    end_date = datetime.utcnow() if end is None else _parse_day(end, "end")

    if start is None:
        start_date = end_date - timedelta(days=days)
    else:
        start_date = _parse_day(start, "start")

    return (
        start_date.strftime("%Y-%m-%dT00:00:00Z"),
        end_date.strftime("%Y-%m-%dT23:59:59Z"),
    )

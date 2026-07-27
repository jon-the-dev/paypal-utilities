"""
Tests for paypal_utils module.
"""

from datetime import datetime, timedelta

import click
import pytest

from paypal_utils import parse_date_range


class TestExplicitDates:
    """Tests for explicitly supplied start and end dates."""

    def test_start_and_end_cover_whole_days(self):
        """A full range starts at midnight and ends one second before the next day."""
        start, end = parse_date_range(start="2024-01-01", end="2024-01-31")

        assert start == "2024-01-01T00:00:00Z"
        assert end == "2024-01-31T23:59:59Z"

    def test_same_start_and_end_is_a_single_day(self):
        """A single-day range is valid."""
        start, end = parse_date_range(start="2024-06-15", end="2024-06-15")

        assert start == "2024-06-15T00:00:00Z"
        assert end == "2024-06-15T23:59:59Z"

    def test_days_is_ignored_when_both_dates_given(self):
        """An explicit start wins over the days lookback."""
        start, end = parse_date_range(start="2024-01-01", end="2024-01-31", days=5)

        assert start == "2024-01-01T00:00:00Z"
        assert end == "2024-01-31T23:59:59Z"


class TestDefaults:
    """Tests for the days-based lookback defaults."""

    def test_end_defaults_to_today(self):
        """Without an end date the range ends on the current UTC day."""
        _, end = parse_date_range(days=30)

        assert end == datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

    def test_start_defaults_to_days_before_end(self):
        """Without a start date the range begins days before the end date."""
        start, _ = parse_date_range(days=30)
        expected = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")

        assert start == expected

    def test_end_given_start_derived(self):
        """A supplied end date anchors the days lookback."""
        start, end = parse_date_range(end="2024-12-31", days=7)

        assert start == "2024-12-24T00:00:00Z"
        assert end == "2024-12-31T23:59:59Z"

    def test_start_given_end_defaults_to_today(self):
        """A supplied start date leaves the end at the current UTC day."""
        start, end = parse_date_range(start="2024-03-01")

        assert start == "2024-03-01T00:00:00Z"
        assert end == datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")

    def test_zero_days_is_a_single_day(self):
        """days=0 yields a range covering only the end date."""
        start, end = parse_date_range(end="2024-05-10", days=0)

        assert start == "2024-05-10T00:00:00Z"
        assert end == "2024-05-10T23:59:59Z"


class TestBoundaries:
    """Tests for calendar edge cases."""

    def test_leap_day_is_accepted(self):
        """29 February in a leap year is a valid date."""
        start, end = parse_date_range(start="2024-02-29", end="2024-02-29")

        assert start == "2024-02-29T00:00:00Z"
        assert end == "2024-02-29T23:59:59Z"

    def test_lookback_crosses_leap_day(self):
        """The lookback must count real calendar days across a leap day."""
        start, _ = parse_date_range(end="2024-03-01", days=1)

        assert start == "2024-02-29T00:00:00Z"

    def test_lookback_crosses_year_boundary(self):
        """The lookback must roll back into the previous year."""
        start, _ = parse_date_range(end="2024-01-02", days=3)

        assert start == "2023-12-30T00:00:00Z"


class TestValidation:
    """Tests for input validation."""

    @pytest.mark.parametrize("bad_date", ["2024-13-01", "01-01-2024", "2024/01/01", "not-a-date", ""])
    def test_invalid_start_raises_bad_parameter(self, bad_date):
        """A malformed start date must be rejected with a clear message."""
        with pytest.raises(click.BadParameter) as exc_info:
            parse_date_range(start=bad_date)

        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_invalid_end_raises_bad_parameter(self):
        """A malformed end date must be rejected with a clear message."""
        with pytest.raises(click.BadParameter) as exc_info:
            parse_date_range(end="2024-02-30")

        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_negative_days_raises_bad_parameter(self):
        """A negative lookback must be rejected rather than inverting the range."""
        with pytest.raises(click.BadParameter) as exc_info:
            parse_date_range(days=-5)

        assert "zero or greater" in str(exc_info.value)

    def test_negative_days_rejected_even_when_unused(self):
        """days is still validated even when it is unused."""
        with pytest.raises(click.BadParameter):
            parse_date_range(start="2024-01-01", end="2024-01-31", days=-1)

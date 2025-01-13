from ttcli.utils import get_week_span
from datetime import date


def test_get_week_span():
    year = 2025
    week = 2
    span = get_week_span(week, year)
    assert span.start_date == date(year, 1, 6)
    assert span.end_date == date(year, 1, 12)


def test_get_week_span_2024():
    year = 2024
    week = 2
    span = get_week_span(week, year)
    assert span.start_date == date(year, 1, 8)
    assert span.end_date == date(year, 1, 14)

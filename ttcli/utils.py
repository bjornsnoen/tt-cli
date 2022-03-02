from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache
from typing import Callable, TypeVar

# Necessary for python < 3.10, could be directly imported from typing
from typing_extensions import ParamSpec


@dataclass
class WeekSpan:
    start_date: date
    end_date: date


def get_week_span(week: int) -> WeekSpan:
    year = date.today().year
    start_datetime = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
    end_datetime = start_datetime + timedelta(days=6)

    return WeekSpan(start_datetime, end_datetime)


def get_week_number(day: date = date.today()) -> int:
    calendar = day.isocalendar()
    return calendar.week


P = ParamSpec("P")
R = TypeVar("R")


def typed_cache(func: Callable[P, R]) -> Callable[P, R]:
    """Because the builtin cache throws away basically all type annotations.
    Use this as a function/method decorator to preserve type information."""
    return cache(func)

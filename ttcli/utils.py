from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache
from typing import Callable, TypeVar

from dateutil.relativedelta import relativedelta

# Necessary for python < 3.10, could be directly imported from typing
from typing_extensions import ParamSpec


@dataclass
class TimeSpan:
    start_date: date
    end_date: date

    def __iter__(self):
        self._iter_index = 0
        return self

    def __next__(self) -> date:
        if self._iter_index == 0:
            self._iter_index += 1
            return self.start_date
        elif self._iter_index == 1:
            self._iter_index += 1
            return self.end_date
        else:
            raise StopIteration


def get_week_span(week: int) -> TimeSpan:
    year = date.today().year
    start_datetime = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").date()
    end_datetime = start_datetime + timedelta(days=6)

    return TimeSpan(start_datetime, end_datetime)


def get_week_number(day: date = date.today()) -> int:
    calendar = day.isocalendar()
    return calendar.week


P = ParamSpec("P")
R = TypeVar("R")


def typed_cache(func: Callable[P, R]) -> Callable[P, R]:
    """Because the builtin cache throws away basically all type annotations.
    Use this as a function/method decorator to preserve type information."""
    return cache(func)  # type: ignore


def get_month_span(
    month: int, include_future: bool = False, year: int = datetime.today().year
) -> TimeSpan:
    first_day = datetime.strptime(f"{year}-{month}-1", "%Y-%m-%d").date()
    last_day_of_month = first_day + relativedelta(months=1, days=-1)
    last_day = (
        min(last_day_of_month, date.today())
        if not include_future
        else last_day_of_month
    )

    return TimeSpan(first_day, last_day)


def week_number(day: date) -> int:
    return int(day.strftime("%W"))

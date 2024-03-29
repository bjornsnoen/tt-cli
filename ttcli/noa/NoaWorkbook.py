from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cached_property
from json import loads
from json.decoder import JSONDecodeError
from os import environ, getenv
from pathlib import Path
from textwrap import dedent
from typing import Optional

import click
from babel.dates import format_date
from click_help_colors.core import HelpColorsGroup
from jinja2 import Environment, FileSystemLoader
from requests.sessions import Session
from rich import print
from rich.console import Console
from rich.prompt import Prompt
from weasyprint import HTML

from ttcli.ApiClient import ApiClient, ConfigurationException
from ttcli.config.config import (
    clear_service_config,
    configure_command,
    source_config,
    write_config,
)
from ttcli.noa.types import (
    NoaDateVisualization,
    NoaTimesheetEntry,
    NoaTimesheetEntryPartial,
)
from ttcli.utils import (
    days_of_week,
    get_month_span,
    get_week_number,
    get_week_span,
    typed_cache,
)

NOA_USERNAME_KEY = "NOA_USERNAME"
NOA_PASSWORD_KEY = "NOA_PASSWORD"


class NoaWorkbook(ApiClient):
    def __init__(
        self, client: Session = Session(), base_url="https://noa.workbook.net/api/"
    ):
        if not self.is_configured():
            missing_keys = [
                k for k in [NOA_USERNAME_KEY, NOA_PASSWORD_KEY] if k not in environ
            ]
            raise ConfigurationException(
                "Noa Workbook not configured", missing_key=",".join(missing_keys)
            )
        super().__init__(client, base_url)

    @classmethod
    def name(cls) -> str:
        return "Noa Workbook"

    def is_configured(self) -> bool:
        return all(k in environ for k in (NOA_USERNAME_KEY, NOA_PASSWORD_KEY))

    @cached_property
    def login(self):
        response = self.api_post(
            "/auth/handshake",
            post_params={
                "UserName": getenv(NOA_USERNAME_KEY),
                "Password": getenv(NOA_PASSWORD_KEY),
                "RememberMe": False,
            },
        )
        return loads(response)

    @cached_property
    def employee_id(self) -> int:
        return self.login["Id"]

    def lock_day(self, day: date = date.today()):
        pass

    def get_day_visualization(self, date=date.today()) -> NoaDateVisualization:
        result = self.api_get(
            "json/reply/TimeEntrySheetVisualizationRequest",
            {"ResourceId": self.employee_id, "Date": date.isoformat()},
        )
        return NoaDateVisualization.parse_obj(loads(result)[0])

    def write_hours(
        self, hours: float, description: str, day: date = date.today()
    ) -> NoaTimesheetEntryPartial:
        days = self.get_week_days(week=get_week_number(day))
        work_day = next(d for d in days if d.post_date.date() == day)
        result = self.api_post(
            "/json/reply/TimeEntryUpdateRequest",
            post_params={
                "Id": work_day.id,
                "Activityid": work_day.activity_id,
                "Billable": True,
                "Hours": hours,
                "TaskId": work_day.task_id,
                "Description": description,
            },
        )
        return NoaTimesheetEntryPartial.parse_obj(loads(result))

    @typed_cache
    def get_week_days(self, week: int) -> list[NoaTimesheetEntry]:
        span = get_week_span(week)
        response = loads(
            self.api_get(
                "/json/reply/TimeEntryDailyRequest",
                {"ResourceId": self.employee_id, "Date": span.start_date, "Week": True},
            )
        )

        return [
            NoaTimesheetEntry.parse_obj(entry)
            for entry in response
            if "TaskId" in entry
        ]

    def get_logged_during_week(self, week: int) -> list[NoaTimesheetEntry]:
        return [entry for entry in self.get_week_days(week) if entry.hours is not None]

    def get_open_days(self, week: int) -> list[NoaTimesheetEntry]:
        return [entry for entry in self.get_week_days(week) if entry.hours is None]


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def noa_command():
    """Commands for the Noa Workbook application"""
    pass


def timesheet(
    week: int,
    client: Optional[NoaWorkbook] = None,
    first_day_mask: Optional[date] = None,
) -> list[NoaTimesheetEntry]:
    if not client:
        client = NoaWorkbook()

    result = [
        entry
        for entry in client.get_logged_during_week(week)
        if entry.description is not None
    ]
    result.sort(key=lambda entry: entry.post_date)
    if first_day_mask:
        result = [entry for entry in result if entry.post_date.date() >= first_day_mask]

    for entry in result:
        hours = entry.hours
        when = entry.registration_date.date()
        description = entry.description
        day = when.strftime("%A")
        hour_color = "yellow" if hours == 7.5 else "red"

        print(f"[green]{day}[/green] [bright_black]({when.isoformat()})[/bright_black]")
        print(f"[{hour_color}]{hours}[/{hour_color}]: {description}")
        print("[bright_black]--[/bright_black]")

    if first_day_mask and len(result) == 0:
        pass
    else:
        print(
            f"[green]Total w{week}:[/green] {sum([entry.hours for entry in result if entry.hours is not None])}h"
        )
    return result


@noa_command.command(name="timesheet")
@click.argument("week", type=int, default=get_week_number(date.today()))
def timesheet_week(week: int):
    timesheet(week)


@noa_command.command()
@click.argument("month", type=int, default=datetime.today().month)
@click.option("--include-future/--no-include-future", default=False)
def timesheet_month(month: int, include_future: bool):
    client = NoaWorkbook()
    first_day, last_day = get_month_span(month, include_future=include_future)
    first_week, last_week = get_week_number(first_day), get_week_number(last_day)
    if first_week > last_week and first_week == 52:
        first_week = 1

    weeks = []

    for week in range(first_week, last_week + 1):
        result = list(
            filter(
                lambda entry: entry.post_date.month == month,
                timesheet(week, client, first_day_mask=first_day),
            )
        )
        if len(result):
            weeks.append(result)
        print("[bright_black bold]--\n[/bright_black bold]")

    print(f"\n[yellow bold]Month summary for {first_day.strftime('%B')}:[/yellow bold]")
    month_total = 0
    for result in weeks:
        week_total = sum([entry.hours for entry in result])
        month_total += week_total
        week_number = result[0].post_date.strftime("%W")
        print(f"[green]Total w{week_number}:[/green] {week_total}h")

    print("[bright_black]--[/bright_black]")
    print(f"[green]Total {first_day.strftime('%b')}:[/green] {month_total}")


def _configure():
    """Configure Noa Workbook"""
    print("[yellow]Please fill in your Noa credentials[/yellow]")
    username = Prompt.ask("Username")
    password = Prompt.ask(
        "Password [dim italic](won't be visible)[/dim italic]", password=True
    )

    write_config(NoaWorkbook, {NOA_USERNAME_KEY: username, NOA_PASSWORD_KEY: password})
    source_config()

    try:
        client = NoaWorkbook()
        default_activity = client.get_day_visualization()
    except JSONDecodeError:
        print("[red]Wrong username or password[/red]")
        clear_service_config(NoaWorkbook)
        return 1

    console = Console(highlight=False)
    console.print(
        dedent(
            f"""
            [green]Success![/green]
            You are good to go :partying_face:
            Your hours will be logged to the following task when using [yellow]tt-a[/yellow]

            * Client: {default_activity.customer_name}
            * Job: {default_activity.job_name}
            * Task: {default_activity.task_description}
            """
        )
    )


@noa_command.command()
def configure():
    _configure()


@configure_command.command(name="noa")
def configure_subcommand():
    _configure()


@noa_command.command()
@click.argument("hours", type=float)
@click.argument("description")
@click.option(
    "-d",
    "--date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
)
@click.option(
    "-D",
    "--weekday",
    type=click.Choice(
        days_of_week,
        case_sensitive=False,
    ),
)
def hours(hours: float, description: str, date: datetime, weekday: str):
    if weekday is not None:
        weekday_index = days_of_week.index(weekday) % 7
        monday = date - timedelta(days=date.weekday())
        date = monday + timedelta(days=weekday_index)

    client = NoaWorkbook()
    client.write_hours(hours, description, date.date())

    print("[green]Done![/green]")


@noa_command.command()
@click.argument("month", type=int, default=datetime.today().month)
@click.option("--include-future/--no-include-future", default=False)
@click.option("--report")
def report(month: int, include_future: bool, report: Path | None):
    client = NoaWorkbook()
    first_day, last_day = get_month_span(month, include_future=include_future)
    first_week, last_week = get_week_number(first_day), get_week_number(last_day)
    if first_week > last_week and first_week == 52:
        first_week = 1

    class SimplifiedEntry:
        day: str
        hours: float
        description: str

        def __init__(self, entry: NoaTimesheetEntryPartial):
            self.day = format_date(entry.post_date, format="EEEE", locale="nb_NO")
            self.hours = entry.hours or 0
            self.description = entry.description or ""

    @dataclass
    class Week:
        entries: list[SimplifiedEntry]
        total: float

    weeks: dict[int, Week] = {}

    for week in range(first_week, last_week + 1):
        result: list[NoaTimesheetEntryPartial] = list(
            filter(
                lambda entry: entry.post_date.month == month,
                timesheet(week, client, first_day_mask=first_day),
            )
        )
        if len(result):
            weeks[week] = Week(
                entries=[SimplifiedEntry(entry) for entry in result],
                total=sum([entry.hours for entry in result if entry.hours is not None]),
            )

    month_total = sum([week.total for week in weeks.values()])

    if report:
        env = Environment(loader=FileSystemLoader(Path(__file__).parent))
        template = env.get_template("report.html")
        html_out = template.render(
            {
                "weeks": weeks,
                "month_total": month_total,
                "month": format_date(first_day, format="MMMM", locale="nb_NO"),
                "year": first_day.year,
                "name": client.login["Name"],
                "total": month_total,
            }
        )
        HTML(string=html_out).write_pdf(report)


if __name__ == "__main__":
    timesheet(week=datetime.today().isocalendar().week)

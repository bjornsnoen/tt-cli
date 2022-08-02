from datetime import date, datetime
from functools import cached_property
from json import loads
from json.decoder import JSONDecodeError
from os import environ, getenv
from pathlib import Path
from textwrap import dedent
from typing import Optional

import click
from click_help_colors.core import HelpColorsGroup
from dotenv import set_key
from dotenv.main import load_dotenv
from inflection import camelize
from pydantic import BaseModel, Extra
from requests.sessions import Session
from rich import print
from rich.console import Console
from rich.prompt import Prompt

from ttcli.ApiClient import ApiClient, ConfigurationException
from ttcli.config import (
    DBConfig,
    clear_config,
    configure_command,
    requires_db,
    source_config,
    write_config,
)
from ttcli.utils import get_month_span, get_week_number, get_week_span, typed_cache

NOA_USERNAME_KEY = "NOA_USERNAME"
NOA_PASSWORD_KEY = "NOA_PASSWORD"


class NoaTimesheetEntryPartial(BaseModel):
    activity_id: int
    approval_status: int
    billable: bool
    correction: int
    cost: float
    cost_currency_amount: float
    cost_currency_id: int
    cost_method: int
    create_date: datetime
    create_resource_id: int
    deleted_marked: bool
    description_required: bool
    hours_moved: float
    id: int
    job_id: int
    journal_number: int
    post_date: datetime
    pricelist_id: int
    public: bool
    registration_date: datetime
    resource_id: int
    sale: float
    sale_currency_amount: float
    sale_currency_id: int
    sequence_number: int
    tariff_additional_percent_cost: float
    tariff_additional_percent_ic_sale: float
    tariff_additional_percent_sale: float
    task_id: int
    update_date: datetime
    update_resource_id: int
    update_type: int
    description: Optional[str] = None
    has_approved_resource_initals: Optional[str] = None
    hours: Optional[float] = None

    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True
        extra = Extra.forbid


class NoaTimesheetEntry(NoaTimesheetEntryPartial):
    access: bool
    can_edit: bool
    can_edit_week: bool
    lock_description: str
    lock_number: int
    locked: bool
    pinned: bool
    sequence_has_entry: bool
    task_hours: float
    task_hours_time_registration: float
    task_phase_name: str


class NoaDateVisualization(BaseModel):
    access: bool
    activity_id: int
    activity_text: str
    customer_id: int
    customer_name: str
    first_reg_date: str
    id: int
    job_id: int
    job_name: str
    pinned: bool
    project_id: int
    project_name: str
    resource_id: int
    sequence_number: int
    task_description: str
    task_hours: float
    task_hours_time_registration: float
    task_id: int
    task_phase_name: str

    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True


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
        return self.login()["Id"]

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

        return [NoaTimesheetEntry.parse_obj(entry) for entry in response]

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
    week: int, client: Optional[NoaWorkbook] = None
) -> list[NoaTimesheetEntry]:
    if not client:
        client = NoaWorkbook()

    result = [
        entry
        for entry in client.get_logged_during_week(week)
        if entry.description is not None
    ]
    result.sort(key=lambda entry: entry.post_date)
    for entry in result:
        hours = entry.hours
        when = entry.post_date.date()
        description = entry.description
        day = when.strftime("%A")
        hour_color = "yellow" if hours == 7.5 else "red"

        print(f"[green]{day}[/green] [bright_black]({when.isoformat()})[/bright_black]")
        print(f"[{hour_color}]{hours}[/{hour_color}]: {description}")
        print("[bright_black]--[/bright_black]")

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
    weeks = []

    for week in range(get_week_number(first_day), get_week_number(last_day) + 1):
        result = list(
            filter(
                lambda entry: entry.post_date.month == month,
                timesheet(week, client),
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
        clear_config(NoaWorkbook)
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

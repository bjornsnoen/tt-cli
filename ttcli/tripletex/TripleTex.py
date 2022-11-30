from dataclasses import dataclass
from datetime import date, datetime, timedelta
from json import dumps, loads
from os import environ, getenv
from textwrap import dedent

import click
from click_help_colors import HelpColorsCommand, HelpColorsGroup
from requests import JSONDecodeError, Session, post
from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from ttcli.ApiClient import ApiClient, ConfigurationException
from ttcli.config.config import (
    clear_service_config,
    configure_command,
    read_service_config,
    source_config,
    write_config,
)
from ttcli.output import print
from ttcli.tripletex.types import (
    ActivityDTO,
    ConfiguredActivity,
    EmployeeDTO,
    ProjectDTO,
    SessionTokenResponse,
    TimesheetEntry,
)
from ttcli.utils import get_week_number

TT_EMPLOYEE_TOKEN_KEY = "TT_EMPLOYEE_TOKEN"
TT_SERVICE_URL_KEY = "TT_SERVICE_URL"
TT_CONFIGURED_ACTIVITY_KEY = "TT_CONFIGURED_ACTIVITY"


class TripleTex(ApiClient):
    def __init__(self):
        self.raise_configuration_exception()

        super(TripleTex, self).__init__(client=Session())
        self._token = None
        self._employee = None

    @classmethod
    def name(cls) -> str:
        return "TripleTex"

    def own_config(self) -> dict[str, str] | None:
        db_model = read_service_config(self.__class__)
        if db_model:
            return db_model.config

        return None

    def get_saved_session_token(self) -> SessionTokenResponse | None:
        config = self.own_config()
        if not config:
            return None

        serialized_token = config.get("SESSION_TOKEN")
        if not serialized_token:
            return None

        return SessionTokenResponse(**loads(serialized_token))

    def persist_session_token(self, token: SessionTokenResponse):
        config = self.own_config()
        if not config:
            return

        config["SESSION_TOKEN"] = token.json()
        write_config(self.__class__, config)

    @property
    def login(self) -> EmployeeDTO:
        if self._token is not None:
            return self.employee

        if token := self.get_saved_session_token():
            if token.expiration_date >= date.today():
                self.login = token
                return self.employee

        login_service_url = getenv(TT_SERVICE_URL_KEY, "http://localhost:8000/login")
        employee_token = getenv(TT_EMPLOYEE_TOKEN_KEY, "dev")
        response = post(login_service_url, json={"employeeToken": employee_token})
        token = SessionTokenResponse(**response.json())

        self.login = token
        return self.employee

    @login.setter
    def login(self, value: SessionTokenResponse):
        self.client.auth = ("0", value.token)
        self.base_url = value.api_url.rstrip("/")
        self._token = value
        self.persist_session_token(value)

    def write_hours(
        self,
        hours: float,
        description: str,
        day: date = date.today(),
        activity_id: int | None = None,
        project_id: int | None = None,
    ) -> dict:
        self.login
        try:
            configured_activity = ConfiguredActivity(
                **loads(getenv(TT_CONFIGURED_ACTIVITY_KEY, ""))
            )
            activity_id = (
                activity_id if activity_id else configured_activity.activity.id
            )
            project_id = (
                project_id
                if project_id
                else (
                    configured_activity.project.id
                    if configured_activity.project
                    else None
                )
            )
        except:
            raise ConfigurationException(
                message="Couldn't figure out which tripletex project or activity to log hours to, please run [code]tt-cli configure tripletex[/code]"
            )

        post_params = {
            "activity": {"id": activity_id},
            "employee": {"id": self.employee.employee_id},
            "date": day.isoformat(),
            "hours": hours,
            "comment": description,
        }
        if project_id:
            post_params["project"] = {"id": project_id}

        result: dict = loads(
            self.api_post(
                "timesheet/entry",
                post_params=post_params,
            )
        )
        if result.get("status", 200) == 409:
            next_day = day + timedelta(days=1)
            params = {
                "dateFrom": day.isoformat(),
                "dateTo": next_day.isoformat(),
                "activityId": configured_activity.activity.id,
            }
            if project_id:
                params["projectId"] = project_id

            conflict: dict = loads(
                self.api_get(
                    "timesheet/entry",
                    params=params,
                )
            )
            if conflict["fullResultSize"] < 1:
                raise Exception(
                    "Somehow you've already logged for that day but we can't find the hours to update them"
                )
            conflict_id = conflict["values"][0]["id"]
            response = self.client.put(
                self.base_url + f"/timesheet/entry/{conflict_id}",
                json={
                    "hours": hours,
                    "comment": description,
                },
            )

            result = response.json()

        return result

    def lock_day(self, day: date = date.today()):
        """This isn't a thing in tripletex, but it's in the contract so we pass"""
        pass

    @property
    def employee(self) -> EmployeeDTO:
        if not self._token:
            self.login

        if self._employee is None:
            self._employee = EmployeeDTO(
                **loads(self.api_get("/token/session/>whoAmI"))["value"]
            )
        return self._employee

    def is_configured(self):
        return all(k in environ for k in (TT_EMPLOYEE_TOKEN_KEY, TT_SERVICE_URL_KEY))

    def raise_configuration_exception(self):
        if TT_EMPLOYEE_TOKEN_KEY not in environ:
            raise ConfigurationException(
                message="Missing username", missing_key=TT_EMPLOYEE_TOKEN_KEY
            )
        elif TT_SERVICE_URL_KEY not in environ:
            raise ConfigurationException(
                message="Missing password", missing_key=TT_SERVICE_URL_KEY
            )

    @dataclass
    class RecentActivities:
        general: list[ActivityDTO]
        project: list[tuple[ProjectDTO, list[ActivityDTO]]]

    def get_recent_activities(self) -> RecentActivities:
        projects_resp = loads(self.api_get("/timesheet/entry/>recentProjects"))[
            "values"
        ]
        projects = [ProjectDTO(**proj) for proj in projects_resp]
        general_activities = loads(self.api_get("/timesheet/entry/>recentActivities"))

        result = self.RecentActivities(
            general=[ActivityDTO(**act) for act in general_activities["values"]],
            project=[],
        )

        for project in projects:
            project_activities_resp = loads(
                self.api_get(
                    "/timesheet/entry/>recentActivities",
                    params={"projectId": project.id},
                )
            )
            result.project.append(
                (
                    project,
                    [ActivityDTO(**act) for act in project_activities_resp["values"]],
                )
            )

        return result

    def get_timesheet_week(self, week_number: int) -> list[TimesheetEntry]:
        result = loads(
            self.api_get(
                "/timesheet/week",
                params={
                    "weekYear": f"{date.today().year}-{week_number}",
                    "employeeIds": self.employee.employee_id,
                    "fields": "timesheetEntries(project(*),activity(*),*)",
                },
            )
        )
        return [
            TimesheetEntry(**data) for data in result["values"][0]["timesheetEntries"]
        ]


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def tripletex_command():
    """Commands for the tripletex application.

    In order to log hours to tripletex, you will need to set a consumer token, an employee token, as well as an activity id
    against which to log the hours. You set these as environment variables, which can either be global or in the .env file
    of this application. The environment variables are:

    TRIPLETEX_CONSUMER_TOKEN\n
    TRIPLETEX_EMPLOYEE_TOKEN\n
    TRIPLETEX_DEFAULT_ACTIVITY_ID

    You can find the activity id using the find subcommand.
    """
    pass


@tripletex_command.command(
    name="find",
    cls=HelpColorsCommand,
    help_headers_color="yellow",
    help_options_color="green",
)
@click.argument("name")
@click.option(
    "-j",
    "--json",
    is_flag=True,
    default=False,
    help="Output as json with additional activity data from the api call instead of formatted list",
)
def find_activities(name: str, json: bool):
    """Iterate over all activities applicable to employee's timesheet looking for a name that matches.
    This will give you the activity id, which you will need to set as an environment variable.

    NAME is part of (or the entirety of) the activity you are looking for. It is case insensitive.
    """
    tripletex = TripleTex()
    tripletex.login
    result: dict = loads(tripletex.api_get("/activity", {"name": name}))

    if result["count"] == 0:
        click.echo(
            """Sorry, we couldn't find that activity.
            Double check that you spelled it just like how it appears in the dropdown in your timesheet."""
        )
    else:
        if json:
            print(dumps(result))
            return

        for i, activity in enumerate(result["values"], start=1):
            print(f'Name: [green]{activity["name"]}[/green]')
            print(f'Activity ID: [green]{str(activity["id"])}[/green]')
            if i < len(result["values"]):
                print("[bright_black]--[/bright_black]")


@tripletex_command.command(
    name="hours",
    cls=HelpColorsCommand,
    help_headers_color="yellow",
    help_options_color="green",
)
@click.argument("hours", type=float)
@click.argument("comment")
@click.option("-a", "--activity-id", type=int)
@click.option(
    "-d",
    "--day",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
)
def write_to_other_activity(
    hours: float, comment: str, activity_id: int, day: datetime
):
    """Write hours to an activity. By default we write to the activity defined by the TRIPLETEX_DEFAULT_ACTIVITY_ID
    environment variable, but a different variable can be specified via the -a option."""
    day_actual = day.date()
    tt = TripleTex()
    try:
        tt.write_hours(
            hours=hours, description=comment, activity_id=activity_id, day=day_actual
        )
        print("f[green]Done![/green]")
    except ConfigurationException as e:
        print(f"[blink]Warning:[/blink] {e.message}")


def _configure():
    """Configure TripleTex"""
    print("[yellow]Please fill in your TripleTex credentials[/yellow]")
    employee_token = Prompt.ask("Employee token")
    login_service_url = Prompt.ask(
        "Service url [gray](must include http(s) and /login parts)[/gray]"
    )

    write_config(
        TripleTex,
        {
            TT_EMPLOYEE_TOKEN_KEY: employee_token,
            TT_SERVICE_URL_KEY: login_service_url,
        },
    )
    source_config()

    try:
        client = TripleTex()
        client.login
    except JSONDecodeError:
        print("[red]Wrong token or url[/red]")
        clear_service_config(TripleTex)
        return 1

    recents = client.get_recent_activities()

    console = Console(highlight=False)
    table = Table(title="[purple]Activitites[/purple]")
    table.add_column("", style="green")
    table.add_column("Project", justify="center")
    table.add_column("Activity", justify="center")

    idx = 1
    choice_values: list[ConfiguredActivity] = []

    for project, activities in recents.project:
        for activity in activities:
            table.add_row(
                str(idx),
                project.display_name,
                activity.display_name,
            )
            choice_values.append(
                ConfiguredActivity(activity=activity, project=project, is_project=True)
            )
            idx += 1

    for activity in recents.general:
        table.add_row(
            str(idx),
            "General",
            activity.display_name,
        )
        choice_values.append(ConfiguredActivity(activity=activity, is_project=False))
        idx += 1

    console.print(table)

    chosen_activity_idx = (
        IntPrompt.ask(
            "Which should be the default activity to log hours to?",
            choices=[str(i) for i in range(1, idx)],
            show_choices=True,
        )
        - 1
    )
    selected_activity = choice_values[chosen_activity_idx]

    write_config(
        TripleTex,
        {
            TT_EMPLOYEE_TOKEN_KEY: employee_token,
            TT_SERVICE_URL_KEY: login_service_url,
            TT_CONFIGURED_ACTIVITY_KEY: selected_activity.json(),
        },
    )

    console.print(
        dedent(
            f"""
            [green]Success![/green]
            You are good to go :partying_face:
            All hours will be logged to [yellow]{selected_activity.project.display_name if selected_activity.project else ''} {selected_activity.activity.display_name}[/yellow]
            """
        )
    )


@tripletex_command.command()
def configure():
    _configure()


@configure_command.command(name="tripletex")
def configure_subcommand():
    _configure()


@tripletex_command.command()
@click.argument("week", type=int, default=get_week_number())
def timesheet(week: int):
    client = TripleTex()
    entries = client.get_timesheet_week(week)

    for entry in entries:
        when = entry.date
        day = when.strftime("%A")
        hour_color = "yellow" if entry.hours == 7.5 else "red"

        print(f"[green]{day}[/green] [bright_black]({when.isoformat()})[/bright_black]")
        print(f"[{hour_color}]{entry.hours}[/{hour_color}]: {entry.comment}")
        print("[bright_black]--[/bright_black]")


if __name__ == "__main__":
    tt = TripleTex()
    _configure()

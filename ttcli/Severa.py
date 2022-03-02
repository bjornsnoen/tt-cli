from datetime import date, datetime, timedelta
from functools import cached_property
from json import load, loads
from os import environ, getenv
from pathlib import Path
from typing import Dict, List, Optional

import click
import requests
from bs4 import BeautifulSoup
from click_help_colors import HelpColorsGroup
from dateutil.parser import parse
from dateutil.tz import tzutc

from ttcli.ApiClient import ApiClient, ConfigurationException, cachebust
from ttcli.output import print
from ttcli.utils import get_month_span

SEVERA_USERNAME_KEY = "SEVERA_USERNAME"
SEVERA_PASSWORD_KEY = "SEVERA_PASSWORD"


class Severa(ApiClient):
    def __init__(self):
        self.raise_configuration_exception()
        self._token: Optional[dict] = None
        self.client = requests.session()
        api_version = "v0.1"
        base_url = "https://severa.visma.com/psarest/{api_version}/".format(
            api_version=api_version
        )
        self.cachepath = Path("/tmp/severauth")
        super(Severa, self).__init__(client=self.client, base_url=base_url)

    @classmethod
    def name(cls):
        return "Severa"

    @cached_property
    def login(self) -> dict:
        def fetch_fresh_access_token() -> dict:
            login_page = self.api_get(
                "/authentication/ExternalLogin",
                {
                    "provider": "VismaConnect",
                    "redirect_uri": "https://severa.visma.com",
                },
            )

            login_soup = BeautifulSoup(login_page, "html5lib")
            login_response = self.client.post(
                "https://connect.visma.com/password",
                data=self.get_login_post_body(login_soup),
            )

            data_soup = BeautifulSoup(login_response.text, "html5lib")

            id_token = data_soup.find("input", attrs={"name": "id_token"})["value"]  # type: ignore
            scope = data_soup.find("input", attrs={"name": "scope"})["value"]  # type: ignore
            code = data_soup.find("input", attrs={"name": "code"})["value"]  # type: ignore
            session_state = data_soup.find("input", attrs={"name": "session_state"})[  # type: ignore
                "value"
            ]

            auth_token_response = self.api_post(
                "/authentication/vismaConnect/obtainLocalAccessToken",
                {
                    "id_token": id_token,
                    "scope": scope,
                    "code": code,
                    "session_state": session_state,
                },
                get_params={"_": cachebust()},
            )

            with self.cachepath.open("w") as cached:
                cached.write(auth_token_response)

            return loads(auth_token_response)

        def fetch_token_from_cache() -> Optional[dict]:
            if self.cachepath.exists():
                access_token_container = load(self.cachepath.open("r"))
                expiry_date = parse(access_token_container["expiresUtc"])

                timediff = expiry_date - datetime.now(tz=tzutc())
                if timediff.total_seconds() > 10:
                    return access_token_container
            return None

        access_token_container = fetch_token_from_cache()
        if not access_token_container:
            access_token_container = fetch_fresh_access_token()

        self.client.headers["authorization"] = "bearer " + self.login["accessToken"]
        self.client.headers["referer"] = "https://severa.visma.com/"

        return access_token_container

    def get_login_post_body(self, login_soup):
        csrf_token = login_soup.find(
            "input", attrs={"name": "__RequestVerificationToken"}
        )["value"]
        return_url = login_soup.find("input", attrs={"name": "ReturnUrl"})["value"]
        postbody = {
            "Username": getenv(SEVERA_USERNAME_KEY),
            "Password": getenv(SEVERA_PASSWORD_KEY),
            "RememberUsername": False,
            "IsPlatformAuthenticatorAvailable": True,
            "ClientId": "severa",
            "ReturnUrl": return_url,
            "__RequestVerificationToken": csrf_token,
        }
        return postbody

    def write_hours(
        self, hours: float, description: str, day: date = date.today()
    ) -> dict:
        possible_projects = self.get_projects()
        first_project = possible_projects[0]
        phases = self.get_phases(first_project)
        first_phase_of_first_project = phases[0]

        body = {
            "guid": None,
            "workType": first_project["defaultWorkType"],
            "phase": {
                "guid": first_phase_of_first_project["guid"],
                "name": first_phase_of_first_project["name"],
            },
            "customer": first_project["customer"],
            "project": first_project["project"],
            "user": {"guid": self.login["user"]["guid"]},
            "overtime": None,
            "description": description,
            "quantity": hours,
            "eventDate": day.isoformat(),
            "startTime": None,
            "endTime": None,
            "isModifiable": True,
        }

        result = loads(
            self.api_post("/workhours", get_params={"_": cachebust()}, post_params=body)
        )
        return result

    def get_projects(self) -> dict:
        return loads(
            self.api_get(
                self.user_endpoint("/phasetreephases"),
                params={
                    "firstRow": 0,
                    "rowCount": 100,
                    "calculateRowCount": False,
                    "_": cachebust(),
                },
            )
        )

    def get_phases(self, project: dict) -> dict:
        return loads(
            self.api_get(
                self.user_endpoint("/phasetreephases"),
                params={
                    "firstRow": 0,
                    "rowCount": 100,
                    "parentPhaseGuid": project["guid"],
                    "_": cachebust(),
                },
            )
        )

    def user_endpoint(self, endpoint: str):
        return f"/users/{self.login['user']['guid']}/{endpoint}"

    def lock_day(self, day: date = date.today()):
        endpoint = "/users/{user_id}/workdays/{date}".format(
            user_id=self.login["user"]["guid"], date=day.isoformat()
        )
        result = self.client.patch(
            self.endpoint(endpoint),
            params={"_": cachebust()},
            json=[{"op": "replace", "path": "isCompleted", "value": True}],
        ).text
        return loads(result)

    def raise_configuration_exception(self):
        if SEVERA_USERNAME_KEY not in environ:
            raise ConfigurationException(
                message="Missing username", missing_key=SEVERA_USERNAME_KEY
            )
        elif SEVERA_PASSWORD_KEY not in environ:
            raise ConfigurationException(
                message="Missing password", missing_key=SEVERA_PASSWORD_KEY
            )

    def is_configured(self) -> bool:
        return all(k in environ for k in (SEVERA_USERNAME_KEY, SEVERA_PASSWORD_KEY))

    def get_logged_during_week(self, week: int):
        year = date.today().year
        starting_datetime = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
        ending_datetime = starting_datetime + timedelta(days=6)

        return loads(
            self.api_get(
                self.user_endpoint("/workhours"),
                params={
                    "firstRow": 0,
                    "rowCount": 100,
                    "calculateRowCount": True,
                    "startDate": starting_datetime.isoformat(),
                    "endDate": ending_datetime.isoformat(),
                },
            )
        )


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def severa_command():
    """Commands for the severa application"""
    pass


def timesheet(week: int, client: Optional[Severa]) -> List[Dict]:
    if not client:
        client = Severa()

    result: List[Dict] = client.get_logged_during_week(week)
    result.sort(key=lambda entry: entry.get("eventDate"))  # type: ignore
    for entry in result:
        hours = entry["quantity"]
        when = date.fromisoformat(entry["eventDate"])
        description = entry["description"]
        day = when.strftime("%A")
        hour_color = "yellow" if hours == 7.5 else "red"

        print(f"[green]{day}[/green] [bright_black]({when.isoformat()})[/bright_black]")
        print(f"[{hour_color}]{hours}[/{hour_color}]: {description}")
        print("[bright_black]--[/bright_black]")

    print(
        f'[green]Total w{week}:[/green] {sum([float(entry["quantity"]) for entry in result])}h'
    )
    return result


@severa_command.command(name="timesheet")
@click.argument("week", type=int, default=datetime.today().isocalendar()[1])
def timesheet_week(week: int):
    timesheet(week, Severa())


@severa_command.command()
@click.argument("month", type=int, default=datetime.today().month)
@click.option("--include-future/--no-include-future", default=False)
def timesheet_month(month: int, include_future: bool):
    client = Severa()
    first_day, last_day = get_month_span(month, include_future=include_future)

    weeks = []

    for week in range(int(first_day.strftime("%W")), int(last_day.strftime("%W")) + 1):
        result = list(
            filter(
                lambda entry: date.fromisoformat(entry["eventDate"]).month == month,
                timesheet(week, client),
            )
        )
        if len(result):
            weeks.append(result)
        print("[bright_black bold]--\n[/bright_black bold]")

    print(f"\n[yellow bold]Month summary for {first_day.strftime('%B')}:[/yellow bold]")
    month_total = 0
    for result in weeks:
        week_total = sum([float(entry["quantity"]) for entry in result])
        month_total += week_total
        week_number = date.fromisoformat(result[0]["eventDate"]).strftime("%W")
        print(f"[green]Total w{week_number}:[/green] {week_total}h")

    print("[bright_black]--[/bright_black]")
    print(f"[green]Total {first_day.strftime('%b')}:[/green] {month_total}")

from datetime import date, datetime, timedelta
from json import loads, dumps
from os import environ, getenv
from typing import Optional, List, Dict

import click
import requests
from bs4 import BeautifulSoup
from click_help_colors import HelpColorsGroup

from ttcli.ApiClient import ApiClient, ConfigurationException, cachebust

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
        super(Severa, self).__init__(client=self.client, base_url=base_url)

    @classmethod
    def name(cls):
        return "Severa"

    @property
    def login(self):
        if self._token is not None:
            return self._token

        login_page = self.api_get(
            "/authentication/ExternalLogin",
            {"provider": "VismaConnect", "redirect_uri": "https://severa.visma.com"},
        )

        login_soup = BeautifulSoup(login_page, "html5lib")
        login_response = self.client.post(
            "https://connect.visma.com/password",
            data=self.get_login_post_body(login_soup),
        )

        data_soup = BeautifulSoup(login_response.text, "html5lib")

        id_token = data_soup.find("input", attrs={"name": "id_token"})["value"]
        scope = data_soup.find("input", attrs={"name": "scope"})["value"]
        code = data_soup.find("input", attrs={"name": "code"})["value"]
        session_state = data_soup.find("input", attrs={"name": "session_state"})[
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

        self.login = loads(auth_token_response)
        self.client.headers["authorization"] = "bearer " + self.login["accessToken"]
        self.client.headers["referer"] = "https://severa.visma.com/"
        return self._token

    @login.setter
    def login(self, value: dict):
        self._token = value

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
        self, hours: float, description: str, date: date = date.today()
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
            "eventDate": date.isoformat(),
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
        ending_datetime = starting_datetime + timedelta(days=7)

        return loads(self.api_get(self.user_endpoint("/workhours"), params={
            "firstRow": 0,
            "rowCount": 100,
            "calculateRowCount": True,
            "startDate": starting_datetime.isoformat(),
            "endDate": ending_datetime.isoformat()
        }))


@click.group(cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green")
def severa_command():
    """ Commands for the severa application """
    pass


@severa_command.command()
@click.argument("week", type=int, default=datetime.today().isocalendar()[1])
def timesheet(week: int):
    client = Severa()
    result: List[Dict] = client.get_logged_during_week(week)
    result.sort(key=lambda entry: entry.get('eventDate'))
    for entry in result:
        hours = entry["quantity"]
        when = date.fromisoformat(entry["eventDate"])
        description = entry["description"]
        day = when.strftime("%A")

        click.secho(day, fg="green", nl=False)
        click.secho(f" ({when.isoformat()})", fg="bright_black")
        click.secho(f'{hours}: ', fg="yellow" if hours == 7.5 else "red", nl=False)
        click.secho(description)
        click.secho('--', fg='bright_black')

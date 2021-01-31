from datetime import date
from json import loads
from os import getenv
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ttcli.ApiClient import ApiClient, cachebust


class Severa(ApiClient):
    def __init__(self):
        self._token: Optional[dict] = None
        self.client = requests.session()
        api_version = "v0.1"
        base_url = "https://severa.visma.com/psarest/{api_version}/".format(
            api_version=api_version
        )
        super(Severa, self).__init__(client=self.client, base_url=base_url)

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
            "Username": getenv("SEVERA_USERNAME"),
            "Password": getenv("SEVERA_PASSWORD"),
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
        nav = possible_projects[0]
        phases = self.get_phases(nav)
        bistand = phases[0]

        body = {
            "guid": None,
            "workType": nav["defaultWorkType"],
            "phase": {"guid": bistand["guid"], "name": bistand["name"]},
            "customer": nav["customer"],
            "project": nav["project"],
            "user": {"guid": self.login["user"]["guid"]},
            "overtime": None,
            "description": description,
            "quantity": hours,
            "eventDate": date.isoformat(),
            "startTime": None,
            "endTime": None,
            "isModifiable": True,
        }

        result = loads(self.api_post(
            "/workhours", get_params={"_": cachebust()}, post_params=body
        ))
        return result


    def get_projects(self) -> dict:
        endpoint = "/users/{guid}/phasetreephases".format(
            guid=self.login["user"]["guid"]
        )
        return loads(
            self.api_get(
                endpoint,
                params={
                    "firstRow": 0,
                    "rowCount": 100,
                    "calculateRowCount": False,
                    "_": cachebust(),
                },
            )
        )

    def get_phases(self, project: dict) -> dict:
        endpoint = "/users/{guid}/phasetreephases".format(
            guid=self.login["user"]["guid"]
        )
        return loads(
            self.api_get(
                endpoint,
                params={
                    "firstRow": 0,
                    "rowCount": 100,
                    "parentPhaseGuid": project["guid"],
                    "_": cachebust(),
                },
            )
        )

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

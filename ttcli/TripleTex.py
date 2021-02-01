from base64 import b64encode
from datetime import date, datetime, timedelta
from json import dumps, loads
from os import getenv

import click
from click_help_colors import HelpColorsCommand, HelpColorsGroup
from requests import Session

from ttcli.ApiClient import ApiClient


class TripleTex(ApiClient):
    def __init__(self):
        super(TripleTex, self).__init__(
            name="TripleTex", client=Session(), base_url="https://api.tripletex.io/v2/"
        )
        self._token = None
        self._employee = None

    @property
    def login(self):
        if self._token is not None:
            return self._token

        result = self.client.put(
            self.endpoint("/token/session/:create"),
            params={
                "consumerToken": getenv("TRIPLETEX_CONSUMER_TOKEN"),
                "employeeToken": getenv("TRIPLETEX_EMPLOYEE_TOKEN"),
                "expirationDate": date.today() + timedelta(days=1),
            },
        )
        self.login = loads(result.text)["value"]
        return self.login

    @login.setter
    def login(self, value):
        self._token = value
        self.client.headers["Authorization"] = "Basic {token}".format(
            token=self.auth_header
        )

    @property
    def auth_header(self):
        bare = "{username}:{password}".format(username=0, password=self.login["token"])
        as_bytes = str.encode(bare)
        return b64encode(as_bytes).decode("utf-8")

    def write_hours(
        self,
        hours: float,
        description: str,
        date: date = date.today(),
        activity_id: int = int(getenv("TRIPLETEX_DEFAULT_ACTIVITY_ID")),
    ) -> dict:
        result = loads(
            self.api_post(
                "/timesheet/entry",
                post_params={
                    "activity": {"id": activity_id},
                    "employee": {"id": self.employee["employeeId"]},
                    "date": date.isoformat(),
                    "hours": hours,
                    "comment": description,
                },
            )
        )
        return result

    def lock_day(self, day: date = date.today()):
        """ This isn't a thing in tripletex, but it's in the contract so we pass """
        pass

    def api_get(self, path: str, params=None) -> str:
        # Only override in order to ensure we are authed
        len(self.auth_header)
        return super().api_get(path, params)

    def api_post(self, path: str, post_params: dict, get_params: dict = None) -> str:
        # Only override in order to ensure we are authed
        len(self.auth_header)
        return super().api_post(path, post_params, get_params)

    @property
    def employee(self):
        if self._employee is None:
            self._employee = loads(self.api_get("/token/session/>whoAmI"))["value"]
        return self._employee


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def tripletex_command():
    """ Commands for the tripletex application.

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
    """ Iterate over all activities applicable to employee's timesheet looking for a name that matches.
    This will give you the activity id, which you will need to set as an environment variable.

    NAME is part of (or the entirety of) the activity you are looking for. It is case insensitive.
    """
    tripletex = TripleTex()
    result: dict = loads(tripletex.api_get("/activity", {"name": name}))

    if result["count"] == 0:
        click.echo(
            """Sorry, we couldn't find that activity.
            Double check that you spelled it just like how it appears in the dropdown in your timesheet."""
        )
    else:
        if json:
            click.echo(dumps(result))
            return

        for i, activity in enumerate(result["values"], start=1):
            click.secho("Name: ", nl=False)
            click.secho(activity["name"], fg="green")
            click.secho("Project ID: ", nl=False)
            click.secho(str(activity["id"]), fg="green")
            if i < len(result["values"]):
                click.secho("--", fg="bright_black")


@tripletex_command.command(
    name="hours",
    cls=HelpColorsCommand,
    help_headers_color="yellow",
    help_options_color="green",
)
@click.argument("hours", type=float)
@click.argument("comment")
@click.option(
    "-a", "--activity-id", type=int, default=getenv("TRIPLETEX_DEFAULT_ACTIVITY_ID")
)
@click.option(
    "-d",
    "--day",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
)
def write_to_other_activity(
    hours: float, comment: str, activity_id: int, day: datetime
):
    """ Write hours to an activity. By default we write to the activity defined by the TRIPLETEX_DEFAULT_ACTIVITY_ID
    environment variable, but a different variable can be specified via the -a option. """
    day = day.date()
    tt = TripleTex()
    result = tt.write_hours(
        hours=hours, description=comment, activity_id=activity_id, date=day
    )
    click.echo(dumps(result))

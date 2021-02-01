#!/usr/bin/env python
from datetime import date, datetime
from typing import List

import click
from click_help_colors import HelpColorsCommand, HelpColorsGroup

from ttcli.ApiClient import ApiClient
from ttcli.Severa import Severa
from ttcli.TripleTex import TripleTex, tripletex_command


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def cli():
    """ Program for interacting with timesheet providers from the cli """
    pass


@cli.command(
    cls=HelpColorsCommand, help_headers_color="yellow", help_options_color="green"
)
def list():
    """ List all known timesheet services """
    print("Severa")


@cli.command(
    cls=HelpColorsCommand, help_headers_color="yellow", help_options_color="green"
)
@click.argument("hours", type=float)
@click.argument("description")
@click.option("--lock/--no-lock", default=True)
@click.option(
    "-d",
    "--day",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
)
def write_to_all(hours: float, description: str, day: datetime, lock: bool):
    """ Write the given data to all known timesheet services. """
    day = day.date()
    services: List[ApiClient] = [TripleTex()]

    for service in services:
        click.secho(
            message="Writing to {service}".format(service=service.name),
            fg="yellow",
            nl=False,
        )
        service.write_hours(hours, description, day)
        click.secho(message=" Done", fg="green")
        if lock:
            click.secho(
                message="Locking {date} in {service}".format(
                    date=day.isoformat(), service=service.name
                ),
                fg="yellow",
                nl=False,
            )
            service.lock_day()
            click.secho(message=" Done", fg="green")


cli.add_command(tripletex_command, name="tripletex")

if __name__ == "__main__":
    cli()

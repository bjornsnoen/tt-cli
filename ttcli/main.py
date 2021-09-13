#!/usr/bin/env python
from datetime import date, datetime
from typing import List

import click
from click_help_colors import HelpColorsCommand, HelpColorsGroup

from ttcli.ApiClient import (
    ConfigurationException,
    get_all_services,
    get_configured_services,
)
from ttcli.Severa import severa_command
from ttcli.TripleTex import tripletex_command


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def cli():
    """ Program for interacting with timesheet providers from the cli """
    pass


@cli.command(
    cls=HelpColorsCommand, help_headers_color="yellow", help_options_color="green"
)
@click.option(
    "-c",
    "--configured",
    help="List only configured services",
    is_flag=True,
    default=False,
)
def list(configured: bool):
    """ List all known timesheet services """
    if not configured:
        for service in get_all_services():
            print(service.name())
    else:
        for service in get_configured_services():
            print(service.__class__.name())


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
    services = get_configured_services()

    for service in services:
        click.secho(
            message="Writing to {service}".format(service=service.name()),
            fg="yellow",
            nl=False,
        )

        try:
            service.write_hours(hours, description, day)
            click.secho(message=" Done", fg="green")
            if lock:
                click.secho(
                    message="Locking {date} in {service}".format(
                        date=day.isoformat(), service=service.name()
                    ),
                    fg="yellow",
                    nl=False,
                )
                service.lock_day(day=day)
                click.secho(message=" Done", fg="green")
        except ConfigurationException as e:
            click.secho("Warning: ", nl=False, blink=True)
            click.secho(e.message)


cli.add_command(tripletex_command, name="tripletex")
cli.add_command(severa_command, name="severa")

if __name__ == "__main__":
    cli()

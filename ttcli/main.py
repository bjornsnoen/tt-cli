#!/usr/bin/env python
import csv
from datetime import date, datetime
from io import BufferedReader

import click
from click_help_colors import HelpColorsCommand, HelpColorsGroup
from rich import traceback
traceback.install()

from ttcli.ApiClient import (
    ConfigurationException,
    get_all_services,
    get_configured_services,
)
from ttcli.output import print
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
    cls=HelpColorsCommand,
    help_headers_color="yellow",
    help_options_color="green",
    name="write-to-all",
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
def write_to_all_cmd(hours: float, description: str, day: datetime, lock: bool):
    write_to_all(hours, description, day, lock)


@cli.command(
    cls=HelpColorsCommand, help_headers_color="yellow", help_options_color="green"
)
@click.option("--lock/--no-lock", default=True)
@click.argument("file", type=click.File("rb"))
def write_to_all_csv(file: BufferedReader, lock: bool):
    lines = [line.decode() for line in file.readlines()]
    reader = csv.DictReader(lines)
    for item in reader:
        day = datetime.fromisoformat(item["date"])
        description = item["description"]
        hours = float(item["hours"])
        write_to_all(hours, description, day, lock)


def write_to_all(hours: float, description: str, day: datetime, lock: bool):
    """ Write the given data to all known timesheet services. """
    day = day.date()
    services = get_configured_services()

    for service in services:
        print(f"[yellow]Writing to {service.name()}[/yellow]", nl=False)

        try:
            service.write_hours(hours, description, day)
            print(" [green]Done[/green]")
            if lock:
                print(
                    f"[yellow]Locking {day.isoformat()} in {service.name()}[/yellow]",
                    nl=False,
                )
                service.lock_day(day=day)
                print(" [green]Done[/green]")
        except ConfigurationException as e:
            print(f"[blink]Warning:[/blink] {e.message}")


cli.add_command(tripletex_command, name="tripletex")
cli.add_command(severa_command, name="severa")

if __name__ == "__main__":
    cli()

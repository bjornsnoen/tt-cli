#!/usr/bin/env python

import csv
from datetime import date, datetime, timedelta
from io import BufferedReader

import click
from click_help_colors import HelpColorsCommand, HelpColorsGroup
from rich import traceback

from ttcli.config.config import configure_command

traceback.install()

from ttcli.ApiClient import (
    ConfigurationException,
    get_all_services,
    get_configured_services,
    get_configured_services_instances,
)
from ttcli.NoaWorkbook import noa_command
from ttcli.output import print
from ttcli.Severa import severa_command
from ttcli.tripletex.TripleTex import tripletex_command
from ttcli.utils import days_of_week


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def cli():
    """Program for interacting with timesheet providers from the cli"""
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
    """List all known timesheet services"""
    if not configured:
        for service in get_all_services():
            print(service.name())
    else:
        for service in get_configured_services():
            print(service.name())


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
def write_to_all_cmd(
    hours: float, description: str, date: datetime, lock: bool, weekday: str
):
    if weekday is not None:
        weekday_index = days_of_week.index(weekday) % 7
        monday = date - timedelta(days=date.weekday())
        date = monday + timedelta(days=weekday_index)

    write_to_all(hours, description, date, lock)


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
    """Write the given data to all known timesheet services."""
    day_actual = day.date()
    services = get_configured_services_instances()

    for service in services:
        print(f"[yellow]Writing to {service.name()}[/yellow]", nl=False)

        try:
            service.write_hours(hours, description, day_actual)
            print(" [green]Done[/green]")
            if lock:
                print(
                    f"[yellow]Locking {day_actual.isoformat()} in {service.name()}[/yellow]",
                    nl=False,
                )
                service.lock_day(day=day_actual)
                print(" [green]Done[/green]")
        except ConfigurationException as e:
            print(f"[blink]Warning:[/blink] {e.message}")


cli.add_command(tripletex_command, name="tripletex")
cli.add_command(severa_command, name="severa")
cli.add_command(noa_command, name="noa")
cli.add_command(configure_command, name="configure")

if __name__ == "__main__":
    cli()

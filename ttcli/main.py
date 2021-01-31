#!/usr/bin/env python
from datetime import date, datetime
from time import sleep

import click

from ttcli.Severa import Severa


@click.group(invoke_without_command=True)
@click.option("-l", "--list", is_flag=True, default=False, help="List all known timesheet services")
def cli(list: bool):
    """ Write the given data to all known timesheet services. """
    if list:
        print("Severa")
        return


@cli.command()
@click.argument("hours")
@click.argument("description")
@click.option("--lock/--no-lock", default=True)
@click.option(
    "-d",
    "--day",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=date.today().isoformat(),
)
def write_to_all(hours: float, description: str, day: datetime, lock: bool):
    day = day.date()
    severa = Severa()
    click.secho(message="Writing to Severa", fg="yellow", nl=False)
    severa.write_hours(hours, description, day)
    click.secho(message=" Done", fg="green")
    if lock:
        click.secho(message="Locking {date} in Severa".format(date=day.isoformat()), fg="yellow", nl=False)
        severa.lock_day()
        click.secho(message=" Done", fg="green")


if __name__ == "__main__":
    cli()

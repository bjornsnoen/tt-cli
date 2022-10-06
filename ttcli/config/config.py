from dataclasses import dataclass
from functools import wraps
from os import environ
from typing import Callable, Optional, ParamSpec, Sequence, Type, TypeVar

import click
from click_help_colors.core import HelpColorsGroup
from rich import print
from rich.table import Table as RichTable
from sqlalchemy import Column, String, Table, delete, select
from sqlalchemy_utils.types import JSONType, StringEncryptedType

from ttcli.ApiClient import ApiClient
from ttcli.db import Session, mapper_registry, requires_db
from ttcli.key import get_key


@mapper_registry.mapped
@dataclass
class DBConfig:
    __table__ = Table(
        "config",
        mapper_registry.metadata,
        Column("service", String(50), primary_key=True, nullable=False),
        Column(
            "config",
            StringEncryptedType(JSONType, key=get_key()),
            nullable=False,
        ),
    )
    service: str
    config: dict[str, str]


@requires_db
def write_config(service: Type[ApiClient], data: dict[str, str]):
    with Session() as session:
        existing_config = read_service_config(service)
        if existing_config is not None:
            existing_config.config = data
            session.add(existing_config)
        else:
            entry = DBConfig(service=service.name(), config=data)
            session.add(entry)

        session.commit()


@requires_db
def clear_config():
    with Session() as session:
        session.execute(delete(DBConfig))
        session.commit()


P = ParamSpec("P")
R = TypeVar("R")


def clears_on_decrypt_exception(func: Callable[P, R]) -> Callable[P, Optional[R]]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[R]:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            if len(e.args[0]) > 0 and e.args[0] == "Invalid decryption key":
                print("[red]Decryption error[/red]")
                print(
                    "The decryption key in the keyring could not decrypt your service credentials."
                )
                print(
                    "Sadly we have to clear the configured credentials and you will need to log in to your services anew."
                )
                clear_config()
                return None
            raise e

    return wrapper


@clears_on_decrypt_exception
@requires_db
def read_config() -> Sequence[DBConfig]:
    with Session() as session:
        result = session.execute(select(DBConfig))
        return result.scalars().all()


@clears_on_decrypt_exception
@requires_db
def read_service_config(service: Type[ApiClient]) -> Optional[DBConfig]:
    name = service.name()
    with Session() as session:
        result = session.execute(select(DBConfig).where(DBConfig.service == name))
        return result.scalar_one_or_none()


@click.group(
    cls=HelpColorsGroup, help_headers_color="yellow", help_options_color="green"
)
def configure_command():
    """Commands for configuring providers"""
    pass


@configure_command.command(name="list")
def list_config():
    configs = read_config()
    if configs is None:
        print("No services configured")
        return

    for config in configs:
        table = RichTable(title=config.service)
        table.add_column("Variable", style="cyan", justify="right")
        table.add_column("Value", style="magenta")
        for k, v in config.config.items():
            table.add_row(k, v)
        print(table)


def source_config():
    for config in read_config() or []:
        for k, v in config.config.items():
            environ[k] = str(v)


@requires_db
def clear_service_config(service: Type[ApiClient]):
    name = service.name()
    with Session() as session:
        session.execute(delete(DBConfig).where(DBConfig.service == name))
        session.commit()

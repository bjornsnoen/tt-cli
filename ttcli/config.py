from dataclasses import dataclass
from os import environ
from typing import Optional, Sequence, Type

import click
from click_help_colors.core import HelpColorsGroup
from rich import print
from rich.table import Table as RichTable
from sqlalchemy import Column, String, Table, delete, select
from sqlalchemy_utils.types import JSONType, StringEncryptedType

from ttcli.ApiClient import ApiClient
from ttcli.db import Session, mapper_registry, requires_db


@mapper_registry.mapped
@dataclass
class DBConfig:
    __table__ = Table(
        "config",
        mapper_registry.metadata,
        Column("service", String(50), primary_key=True, nullable=False),
        Column(
            "config",
            StringEncryptedType(JSONType, key="tB3A$@otez%cfmh9Ng"),
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
def read_config() -> Sequence[DBConfig]:
    with Session() as session:
        result = session.execute(select(DBConfig))
        return result.scalars().all()


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
    for config in configs:
        table = RichTable(title=config.service)
        table.add_column("Variable", style="cyan", justify="right")
        table.add_column("Value", style="magenta")
        for k, v in config.config.items():
            table.add_row(k, v)
        print(table)


def source_config():
    for config in read_config():
        for k, v in config.config.items():
            environ[k] = v


@requires_db
def clear_config(service: Type[ApiClient]):
    name = service.name()
    with Session() as session:
        session.execute(delete(DBConfig).where(DBConfig.service == name))
        session.commit()

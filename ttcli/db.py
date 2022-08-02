import logging
from functools import cache, wraps
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar

from alembic import command
from alembic.config import Config
from appdirs import user_config_dir
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import registry, sessionmaker

from ttcli.utils import typed_cache

mapper_registry = registry()


def get_db_location() -> str:
    location = user_config_dir(appname="tt-cli", appauthor="brbcoffee")
    db_file = f"sqlite:///{location}/config.sqlite"

    as_path = Path(location)
    if not as_path.exists():
        as_path.mkdir(parents=True)

    return db_file


@typed_cache
def get_engine() -> Engine:
    return create_engine(get_db_location(), future=True)


@cache
def ensure_latest_db_exists():
    logging.getLogger("alembic").setLevel(logging.CRITICAL)
    ini_location = Path(__file__).parent.parent / "alembic.ini"
    alembic_cfg = Config(str(ini_location))
    command.upgrade(alembic_cfg, "head")


P = ParamSpec("P")
R = TypeVar("R")


def requires_db(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapped(*args, **kwargs):
        ensure_latest_db_exists()
        return func(*args, **kwargs)  # type: ignore

    return wrapped  # type: ignore


Session = sessionmaker(get_engine())

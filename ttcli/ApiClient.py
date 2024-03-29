from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import date
from time import time
from typing import Any, Iterable, Optional, Type

from requests import Session


def cachebust():
    return time() * 1000


class ApiClient(ABC, metaclass=ABCMeta):
    def __init__(self, client: Session = Session(), base_url: str = ""):
        self.client = client
        self.base_url = base_url.rstrip("/")
        super().__init__()

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        return "Generic"

    def api_get(self, path: str, params: Optional[dict] = None) -> str:
        if params is None:
            params = {}
        return self.client.get(self.endpoint(path), params=params).text

    def api_post(
        self, path: str, post_params: dict, get_params: Optional[dict] = None
    ) -> str:
        if get_params is None:
            get_params = {}

        return self.client.post(
            self.endpoint(path), json=post_params, params=get_params
        ).text

    def endpoint(self, path) -> str:
        return "{base_url}/{path}".format(base_url=self.base_url, path=path.lstrip("/"))

    @abstractmethod
    def write_hours(
        self, hours: float, description: str, day: date = date.today()
    ) -> Any:
        """:raises: ConfigurationException"""
        pass

    @abstractmethod
    def lock_day(self, day: date = date.today()):
        """:raises: ConfigurationException"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Ensure that all configuration necessary for successful operation is present"""
        pass


@dataclass
class ConfigurationException(BaseException):
    message: str
    missing_key: Optional[str] = None


def get_all_services() -> Iterable[Type[ApiClient]]:
    from ttcli.noa.NoaWorkbook import NoaWorkbook
    from ttcli.Severa import Severa
    from ttcli.tripletex.TripleTex import TripleTex

    return TripleTex, Severa, NoaWorkbook


def get_configured_services_instances() -> Iterable[ApiClient]:
    services = []
    for cls in get_all_services():
        try:
            services.append(cls())
        except ConfigurationException:
            pass

    return services


def get_configured_services() -> Iterable[Type[ApiClient]]:
    services = get_configured_services_instances()
    return [service.__class__ for service in services]


def get_service_by_name(name: str) -> Type[ApiClient]:
    lookup = {service.name(): service for service in get_all_services()}
    return lookup[name]

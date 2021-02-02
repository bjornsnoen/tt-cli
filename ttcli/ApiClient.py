from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import date
from time import time
from typing import List, Optional

from requests import Session


def cachebust():
    return time() * 1000


class ApiClient(ABC, metaclass=ABCMeta):
    def __init__(self, name: str, client: Session, base_url: str):
        self.client = client
        self.base_url = base_url.rstrip("/")
        self._name = name
        super().__init__()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def api_get(self, path: str, params: dict = None) -> str:
        if params is None:
            params = {}
        return self.client.get(self.endpoint(path), params=params).text

    def api_post(self, path: str, post_params: dict, get_params: dict = None) -> str:
        if get_params is None:
            get_params = {}

        return self.client.post(
            self.endpoint(path), json=post_params, params=get_params
        ).text

    def endpoint(self, path) -> str:
        return "{base_url}/{path}".format(base_url=self.base_url, path=path.lstrip("/"))

    @abstractmethod
    def write_hours(
        self, hours: float, description: str, date: date = date.today()
    ) -> dict:
        """ :raises: ConfigurationException """
        pass

    @abstractmethod
    def lock_day(self, day: date = date.today()):
        """ :raises: ConfigurationException """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """ Ensure that all configuration necessary for successful operation is present """
        pass


@dataclass
class ConfigurationException(BaseException):
    message: str
    missing_key: Optional[str]


def get_configured_services() -> List[ApiClient]:
    from ttcli.Severa import Severa
    from ttcli.TripleTex import TripleTex

    services = []
    for cls in (TripleTex, Severa):
        try:
            services.append(cls())
        except ConfigurationException:
            pass

    return services

from abc import ABC, ABCMeta, abstractmethod
from datetime import date
from time import time

from requests import Session


def cachebust():
    return time() * 1000


class ApiClient(ABC, metaclass=ABCMeta):
    def __init__(self, client: Session, base_url: str):
        self.client = client
        self.base_url = base_url
        super().__init__()

    def api_get(self, path: str, params: dict) -> str:
        return self.client.get(self.endpoint(path), params=params).text

    def api_post(self, path: str, post_params: dict, get_params: dict = None) -> str:
        return self.client.post(
            self.endpoint(path), json=post_params, params=get_params
        ).text

    def endpoint(self, path) -> str:
        return "{base_url}/{path}".format(base_url=self.base_url, path=path.lstrip("/"))

    @abstractmethod
    def write_hours(
        self, hours: float, description: str, date: date = date.today()
    ) -> dict:
        pass

    @abstractmethod
    def lock_day(self, day: date = date.today()):
        pass

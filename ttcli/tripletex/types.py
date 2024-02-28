from datetime import date
from re import match

from humps.camel import case as camel_case
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


def is_http_url(value) -> bool:
    class TempModel(BaseModel):
        url: HttpUrl

    try:
        TempModel(url=value)
        return True
    except ValueError:
        return False


class TripletexToken(BaseModel):
    id: int
    url: HttpUrl

    @field_validator("url", mode="before")
    @classmethod
    def inject_scheme(cls, url: str | HttpUrl):
        """TripleTex responds with urls that omit the scheme, which is required"""
        if is_http_url(url):
            return url

        elif match(r"https?://", str(url)):
            return url

        return f"https://{url}"

    model_config = ConfigDict(alias_generator=camel_case, populate_by_name=True)


class SessionToken(TripletexToken):
    version: int
    consumer_token: TripletexToken
    employee_token: TripletexToken
    expiration_date: date
    token: str
    encryption_key: str | None = None


class ApiTokenEnvelope(BaseModel):
    value: SessionToken


class SessionTokenResponse(TripletexToken):
    token: str
    expiration_date: date
    api_url: HttpUrl


class EmployeeDTO(BaseModel):
    employee_id: int
    employee: dict
    company_id: int
    company: dict
    model_config = ConfigDict(alias_generator=camel_case, populate_by_name=True)


class ProjectDTO(BaseModel):
    id: int
    name: str
    display_name: str
    number: int
    model_config = ConfigDict(alias_generator=camel_case, populate_by_name=True)


class ActivityDTO(BaseModel):
    id: int
    is_project_activity: bool
    name: str
    display_name: str
    model_config = ConfigDict(alias_generator=camel_case, populate_by_name=True)


class ConfiguredActivity(BaseModel):
    activity: ActivityDTO
    project: ProjectDTO | None = None
    is_project: bool


class TimesheetEntry(BaseModel):
    activity: ActivityDTO
    project: ProjectDTO | None = None
    date: date
    hours: float
    comment: str
    model_config = ConfigDict(alias_generator=camel_case, populate_by_name=True)

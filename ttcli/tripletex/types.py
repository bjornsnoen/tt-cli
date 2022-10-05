from datetime import date
from re import match

from humps.camel import case as camel_case
from pydantic import BaseConfig, BaseModel, HttpUrl, validator


class TripletexToken(BaseModel):
    id: int
    url: HttpUrl

    @validator("url", pre=True)
    def inject_scheme(cls, url: str | HttpUrl):
        """TripleTex respons with urls that omit the scheme, which is required"""
        if isinstance(url, HttpUrl):
            return url

        if match(r"https?://", url):
            return url

        return f"https://{url}"

    class Config(BaseConfig):
        alias_generator = camel_case
        allow_population_by_field_name = True


class SessionToken(TripletexToken):
    version: int
    consumer_token: TripletexToken
    employee_token: TripletexToken
    expiration_date: date
    token: str
    encryption_key: str | None


class ApiTokenEnvelope(BaseModel):
    value: SessionToken


class SessionTokenResponse(TripletexToken):
    token: str
    expiration_date: date

from os import getenv

from fastapi import Body, FastAPI
from requests import put

from ttcli.tripletex.types import ApiTokenEnvelope, SessionTokenResponse

app = FastAPI()

api_url = "https://api.tripletex.io/v2/"

consumer_token = getenv("TT_CONSUMER_TOKEN")


@app.post("/login", response_model=SessionTokenResponse)
def create_token(employee_token: str = Body(alias="employeeToken", embed=True)):
    response = put(
        api_url + "token/session/:create",
        params={
            "consumerToken": consumer_token,
            "employeeToken": employee_token,
            "expirationDate": "2022-10-06",
        },
    )
    data = response.json()
    return ApiTokenEnvelope(**data).value


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ttcli.tripletex.auth_server:app", reload=True)

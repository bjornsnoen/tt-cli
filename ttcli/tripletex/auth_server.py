from datetime import date, timedelta
from os import getenv

from fastapi import Body, FastAPI, HTTPException
from requests import put

from ttcli.tripletex.types import ApiTokenEnvelope, SessionTokenResponse

app = FastAPI()


consumer_token = getenv("TT_CONSUMER_TOKEN")
prod = getenv("TT_PROD", False)

api_url = "https://tripletex.no/v2/" if prod else "https://api.tripletex.io/v2/"


@app.post(
    "/login",
    response_model=SessionTokenResponse,
)
def create_token(employee_token: str = Body(alias="employeeToken", embed=True)):
    expire_at = date.today() + timedelta(days=7)
    response = put(
        api_url + "token/session/:create",
        params={
            "consumerToken": consumer_token,
            "employeeToken": employee_token,
            "expirationDate": expire_at.isoformat(),
        },
    )
    data = response.json()
    try:
        api_token = ApiTokenEnvelope(**data).value
        response = SessionTokenResponse(**api_token.dict() | {"api_url": api_url})
        return response
    except:
        print(data)
        raise HTTPException(401)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ttcli.tripletex.auth_server:app", reload=True)

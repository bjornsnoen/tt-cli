from python:3.10-alpine

RUN apk add curl gcc libc-dev && curl -sSL https://install.python-poetry.org | python3 -

COPY ./pyproject.toml ./poetry.lock /app/
WORKDIR /app
ENV PATH="${PATH}:/root/.local/bin"
ENV TT_AUTH_PORT=8000

RUN poetry install --no-root
COPY ./ /app
RUN poetry install

CMD ["sh", "-c", "poetry run uvicorn ttcli.tripletex.auth_server:app --port $TT_AUTH_PORT"]

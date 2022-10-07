# syntax=docker/dockerfile:1.3-labs


from python:3.10-alpine as auth

RUN apk add curl gcc libc-dev && curl -sSL https://install.python-poetry.org | python3 -

COPY ./pyproject.toml ./poetry.lock /app/
WORKDIR /app
ENV PATH="${PATH}:/root/.local/bin"
ENV TT_AUTH_PORT=8000

RUN poetry install --no-root
COPY ./ /app
RUN poetry install

COPY <<EOF /app/entrypoint.sh
#!/bin/sh
poetry run uvicorn ttcli.tripletex.auth_server:app \\
    --port $TT_AUTH_PORT \\
    --host 0.0.0.0
EOF
RUN chmod +x /app/entrypoint.sh

LABEL org.opencontainers.image.description="Runs the tripletex auth service for exchanging employee tokens for session tokens"

ENTRYPOINT ["./entrypoint.sh"]


from auth as with-vaultenv
RUN curl -L https://github.com/channable/vaultenv/releases/download/v0.15.1/vaultenv-0.15.1-linux-musl > /bin/vaultenv \
    && chmod +x /bin/vaultenv

ENTRYPOINT ["vaultenv", "./entrypoint.sh"]

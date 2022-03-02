#!/usr/bin/env sh

poetry run black **/*.py
poetry run isort --profile=black **/*.py

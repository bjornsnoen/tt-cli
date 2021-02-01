#!/usr/bin/env sh

pipenv run black **/*.py
pipenv run isort --profile=black **/*.py

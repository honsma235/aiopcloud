#!/bin/bash
git clone https://github.com/honsma235/aiopcloud.git
cd yourrepo
curl -sSL https://install.python-poetry.org | python3 -
poetry install
poetry run pre-commit install --hook-type commit-msg

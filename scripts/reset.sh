#!/usr/bin/env bash

export PYTHONPATH=.

rm data/app.db
uv run alembic upgrade head
uv run scripts/create_user.py --email dev@gmail.com --password dev --role admin
uv run scripts/create_user.py --email adv@gmail.com --password adv --role advisor

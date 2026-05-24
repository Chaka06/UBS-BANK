#!/usr/bin/env bash
set -e
python3 -m venv .venv_build
.venv_build/bin/pip install -q -r requirements.txt
DJANGO_SECRET_KEY=build-collectstatic-key \
DJANGO_DEBUG=0 \
.venv_build/bin/python manage.py collectstatic --noinput

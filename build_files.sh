#!/usr/bin/env bash
set -e
pip install -r requirements.txt
DJANGO_SECRET_KEY=build-collectstatic-key \
DJANGO_DEBUG=0 \
python manage.py collectstatic --noinput

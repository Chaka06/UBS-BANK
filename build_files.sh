#!/usr/bin/env bash
set -e

python3 -m venv .venv_build
.venv_build/bin/pip install -q -r requirements.txt

# 1. Appliquer les migrations
.venv_build/bin/python manage.py migrate --noinput

# 2. Collecter les fichiers statiques
DJANGO_SECRET_KEY=build-collectstatic-key \
DJANGO_DEBUG=0 \
.venv_build/bin/python manage.py collectstatic --noinput

# 3. Créer le superutilisateur (lit ADMIN_EMAIL et ADMIN_PASSWORD depuis les variables d'env)
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    .venv_build/bin/python manage.py create_admin --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD"
fi

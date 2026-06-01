#!/usr/bin/env bash
set -e

python3 -m venv .venv_build
.venv_build/bin/pip install -q -r requirements.txt

# 1. Appliquer les migrations pour être sûr que les tables existent
.venv_build/bin/python manage.py migrate --noinput

# 2. Collecter les fichiers statiques
DJANGO_SECRET_KEY=build-collectstatic-key \
DJANGO_DEBUG=0 \
.venv_build/bin/python manage.py collectstatic --noinput

# 3. Créer le superutilisateur spécifié
echo "
from django.contrib.auth import get_user_model
User = get_user_model()

email = 'ubscite@gmail.com'

User.objects.filter(email=email).delete()

User.objects.create_superuser(
    email,
    '55#gdjt67wQhdjet',
    first_name='adminatilo',
    last_name='User',
    date_of_birth='1980-01-01',
    phone_number='000000',
    address='Vercel',
    country='CH',
    is_active=True
)
" | .venv_build/bin/python manage.py shell

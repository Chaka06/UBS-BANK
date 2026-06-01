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

# 3. Créer le superutilisateur via un script temporaire
cat << 'EOF' > create_admin_tmp.py
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ubsbank.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = 'ubscite@gmail.com'
password = '55#gdjt67wQhdjet'

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        first_name='adminatilo',
        last_name='User',
        date_of_birth=date(1980, 1, 1),
        phone_number='000000',
        address='Vercel',
        country='CH',
        is_active=True
    )
    print(f"User {email} created successfully")
else:
    u = User.objects.get(email=email)
    u.set_password(password)
    u.is_active = True
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print(f"User {email} updated successfully")
EOF

.venv_build/bin/python create_admin_tmp.py
rm create_admin_tmp.py

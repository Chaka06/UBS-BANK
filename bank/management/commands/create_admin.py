import os
from datetime import date
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a superuser admin. Reads ADMIN_EMAIL and ADMIN_PASSWORD from env vars or CLI arguments."

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default=None,
            help='Admin email address (overrides ADMIN_EMAIL env var)',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default=None,
            help='Admin first name (overrides ADMIN_FIRST_NAME env var)',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default=None,
            help='Admin last name (overrides ADMIN_LAST_NAME env var)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Admin password (overrides ADMIN_PASSWORD env var). If omitted, prompted interactively.',
        )

    def handle(self, *args, **options):
        User = get_user_model()

        email = options['email'] or os.environ.get('ADMIN_EMAIL', '').strip()
        if not email:
            email = input('Email: ').strip()
        if not email:
            raise CommandError('Email is required.')

        first_name = (
            options['first_name']
            or os.environ.get('ADMIN_FIRST_NAME', '').strip()
            or 'Admin'
        )
        last_name = (
            options['last_name']
            or os.environ.get('ADMIN_LAST_NAME', '').strip()
            or 'User'
        )

        password = options['password'] or os.environ.get('ADMIN_PASSWORD', '').strip()
        if not password:
            password = getpass('Password: ').strip()
        if not password:
            raise CommandError('Password is required.')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': date(1980, 1, 1),
                'phone_number': '0000000000',
                'address': 'N/A',
                'country': 'CH',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )

        if not created:
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True

        user.set_password(password)
        user.save()

        action = 'created' if created else 'updated'
        self.stdout.write(self.style.SUCCESS(f'Superuser {action}: {user.email}'))

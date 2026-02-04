from datetime import date
from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a superuser with only email and password prompts."

    def handle(self, *args, **options):
        User = get_user_model()
        email = input("Email (username): ").strip()
        if not email:
            raise CommandError("Email is required.")
        if User.objects.filter(email=email).exists():
            raise CommandError("A user with this email already exists.")
        password = getpass("Password: ").strip()
        if not password:
            raise CommandError("Password is required.")

        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name="Admin",
            last_name="User",
            date_of_birth=date(1980, 1, 1),
            phone_number="0000000000",
            address="N/A",
            country="CH",
        )
        self.stdout.write(self.style.SUCCESS(f"Superuser created: {user.email}"))

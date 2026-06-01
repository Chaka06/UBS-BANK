from django.apps import AppConfig


class BankConfig(AppConfig):
    name = 'bank'

    def ready(self):
        from . import signals  # noqa: F401

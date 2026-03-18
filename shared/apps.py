from django.apps import AppConfig


class SharedConfig(AppConfig):
    name = 'shared'

    def ready(self):
        import shared.signals  # noqa

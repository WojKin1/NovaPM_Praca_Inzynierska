from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    name = 'resources'
    verbose_name = 'Zasoby i zespół'
    def ready(self):
        import resources.signals  # noqa

from django.apps import AppConfig


class BudgetConfig(AppConfig):
    name = 'budget'
    verbose_name = 'Budżet i czas pracy'
    def ready(self):
        import budget.signals  # noqa

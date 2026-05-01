from django.conf import settings
from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        INITIATION = 'INITIATION', 'Inicjacja'
        PLANNING = 'PLANNING', 'Planowanie'
        EXECUTION = 'EXECUTION', 'Realizacja'
        MONITORING = 'MONITORING', 'Monitorowanie'
        CLOSED = 'CLOSED', 'Zamknięty'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Niski'
        MEDIUM = 'MEDIUM', 'Średni'
        HIGH = 'HIGH', 'Wysoki'
        CRITICAL = 'CRITICAL', 'Krytyczny'

    name = models.CharField(max_length=200, verbose_name='Nazwa projektu')
    description = models.TextField(blank=True, null=True, verbose_name='Opis')
    client_name = models.CharField(max_length=200, verbose_name='Nazwa klienta')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATION, verbose_name='Status')
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, verbose_name='Priorytet')
    start_date = models.DateField(verbose_name='Data rozpoczęcia')
    end_date = models.DateField(verbose_name='Data zakończenia')
    budget_planned = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Budżet planowany')
    budget_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Budżet wydany')
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_projects',
        verbose_name='Kierownik projektu',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_projects',
        verbose_name='Utworzony przez',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    class Meta:
        verbose_name = 'projekt'
        verbose_name_plural = 'projekty'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

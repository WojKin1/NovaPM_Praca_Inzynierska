from django.conf import settings
from django.db import models

from projects.models import Project


class ChangeRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Szkic'
        SUBMITTED = 'SUBMITTED', 'Złożony'
        ANALYSED = 'ANALYSED', 'Analizowany'
        APPROVED = 'APPROVED', 'Zatwierdzony'
        REJECTED = 'REJECTED', 'Odrzucony'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='change_requests', verbose_name='Projekt')
    title = models.CharField(max_length=200, verbose_name='Tytuł')
    description = models.TextField(verbose_name='Opis')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_changes',
        verbose_name='Wnioskodawca',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, verbose_name='Status')
    impact_scope = models.TextField(verbose_name='Zakres wpływu')
    impact_time = models.IntegerField(help_text='Liczba dni', verbose_name='Wpływ na czas (dni)')
    impact_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Wpływ na koszt')
    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decided_changes',
        verbose_name='Decyzja wydana przez',
    )
    decision_date = models.DateField(null=True, blank=True, verbose_name='Data decyzji')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    class Meta:
        verbose_name = 'wniosek o zmianę'
        verbose_name_plural = 'wnioski o zmianę'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

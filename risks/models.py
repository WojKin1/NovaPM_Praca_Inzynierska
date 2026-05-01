from django.conf import settings
from django.db import models

from projects.models import Project


class Risk(models.Model):
    class Probability(models.IntegerChoices):
        VERY_LOW = 1, 'Bardzo niskie'
        LOW = 2, 'Niskie'
        MEDIUM = 3, 'Średnie'
        HIGH = 4, 'Wysokie'
        VERY_HIGH = 5, 'Bardzo wysokie'

    class Impact(models.IntegerChoices):
        VERY_LOW = 1, 'Bardzo niski'
        LOW = 2, 'Niski'
        MEDIUM = 3, 'Średni'
        HIGH = 4, 'Wysoki'
        VERY_HIGH = 5, 'Bardzo wysoki'

    class Status(models.TextChoices):
        IDENTIFIED = 'IDENTIFIED', 'Zidentyfikowane'
        ANALYSED = 'ANALYSED', 'Analizowane'
        MITIGATED = 'MITIGATED', 'Mitygowane'
        CLOSED = 'CLOSED', 'Zamknięte'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='risks', verbose_name='Projekt')
    title = models.CharField(max_length=200, verbose_name='Tytuł')
    description = models.TextField(blank=True, null=True, verbose_name='Opis')
    probability = models.IntegerField(choices=Probability.choices, verbose_name='Prawdopodobieństwo')
    impact = models.IntegerField(choices=Impact.choices, verbose_name='Wpływ')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_risks',
        verbose_name='Właściciel',
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.IDENTIFIED, verbose_name='Status')
    mitigation_plan = models.TextField(blank=True, null=True, verbose_name='Plan mitygacji')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    class Meta:
        verbose_name = 'ryzyko'
        verbose_name_plural = 'ryzyka'
        ordering = ['-created_at']

    @property
    def risk_level(self):
        return self.probability * self.impact

    def __str__(self):
        return self.title

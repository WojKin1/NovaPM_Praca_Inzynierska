from django.conf import settings
from django.db import models

from projects.models import Project


class Requirement(models.Model):
    class ReqType(models.TextChoices):
        FUNCTIONAL = 'FUNCTIONAL', 'Funkcjonalne'
        NON_FUNCTIONAL = 'NON_FUNCTIONAL', 'Niefunkcjonalne'

    class Priority(models.TextChoices):
        HIGH = 'HIGH', 'Wysoki'
        MEDIUM = 'MEDIUM', 'Średni'
        LOW = 'LOW', 'Niski'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Szkic'
        APPROVED = 'APPROVED', 'Zatwierdzone'
        IMPLEMENTED = 'IMPLEMENTED', 'Zrealizowane'
        REJECTED = 'REJECTED', 'Odrzucone'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='requirements', verbose_name='Projekt')
    code = models.CharField(max_length=20, verbose_name='Kod')
    title = models.CharField(max_length=200, verbose_name='Tytuł')
    description = models.TextField(blank=True, verbose_name='Opis')
    req_type = models.CharField(max_length=15, choices=ReqType.choices, default=ReqType.FUNCTIONAL, verbose_name='Typ wymagania')
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, verbose_name='Priorytet')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT, verbose_name='Status')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_requirements',
        verbose_name='Utworzone przez',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    class Meta:
        verbose_name = 'wymaganie'
        verbose_name_plural = 'wymagania'
        ordering = ['code']
        unique_together = [('project', 'code')]

    def __str__(self):
        return f'{self.code} — {self.title}'


class WBSElement(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='wbs_elements', verbose_name='Projekt')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Element nadrzędny',
    )
    code = models.CharField(max_length=20, default='', verbose_name='Kod')
    name = models.CharField(max_length=200, verbose_name='Nazwa')
    description = models.TextField(blank=True, null=True, verbose_name='Opis')
    order = models.PositiveIntegerField(default=0, verbose_name='Kolejność')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    @property
    def level(self):
        if not self.code:
            return 1
        return self.code.count('.') + 1

    class Meta:
        verbose_name = 'element WBS'
        verbose_name_plural = 'elementy WBS'
        ordering = ['order']

    def __str__(self):
        return f'{self.code} {self.name}'.strip()

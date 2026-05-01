from django.conf import settings
from django.db import models

from projects.models import Project


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'TODO', 'Do zrobienia'
        IN_PROGRESS = 'IN_PROGRESS', 'W trakcie'
        IN_REVIEW = 'IN_REVIEW', 'W przeglądzie'
        DONE = 'DONE', 'Zakończone'
        BLOCKED = 'BLOCKED', 'Zablokowane'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Niski'
        MEDIUM = 'MEDIUM', 'Średni'
        HIGH = 'HIGH', 'Wysoki'
        CRITICAL = 'CRITICAL', 'Krytyczny'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name='Projekt')
    title = models.CharField(max_length=200, verbose_name='Tytuł')
    description = models.TextField(blank=True, null=True, verbose_name='Opis')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name='Przypisany do',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_tasks',
        verbose_name='Utworzone przez',
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.TODO, verbose_name='Status')
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, verbose_name='Priorytet')
    due_date = models.DateField(verbose_name='Termin')
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Szacowane godziny')
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='Rzeczywiste godziny')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Data aktualizacji')

    class Meta:
        verbose_name = 'zadanie'
        verbose_name_plural = 'zadania'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TaskReview(models.Model):
    class Result(models.TextChoices):
        APPROVED = 'APPROVED', 'Zatwierdzone'
        REJECTED = 'REJECTED', 'Odrzucone'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reviews', verbose_name='Zadanie')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='task_reviews',
        verbose_name='Recenzent',
    )
    result = models.CharField(max_length=10, choices=Result.choices, verbose_name='Wynik')
    comment = models.TextField(blank=True, verbose_name='Komentarz')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data przeglądu')

    class Meta:
        verbose_name = 'przegląd zadania'
        verbose_name_plural = 'przeglądy zadań'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task} — {self.result}'

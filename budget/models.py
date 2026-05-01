from django.conf import settings
from django.db import models

from projects.models import Project
from tasks.models import Task


class BudgetCategory(models.Model):
    class CategoryType(models.TextChoices):
        LABOUR = 'LABOUR', 'Praca'
        INFRASTRUCTURE = 'INFRASTRUCTURE', 'Infrastruktura'
        LICENSES = 'LICENSES', 'Licencje'
        OTHER = 'OTHER', 'Inne'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='budget_categories', verbose_name='Projekt')
    name = models.CharField(max_length=200, verbose_name='Nazwa')
    category_type = models.CharField(max_length=20, choices=CategoryType.choices, verbose_name='Typ kategorii')
    planned_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Kwota planowana')
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Kwota wydana')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')

    class Meta:
        verbose_name = 'kategorię budżetu'
        verbose_name_plural = 'kategorie budżetu'
        ordering = ['project', 'name']

    def __str__(self):
        return f'{self.project} — {self.name}'


class Timesheet(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='timesheets', verbose_name='Projekt')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='timesheets',
        verbose_name='Użytkownik',
    )
    date = models.DateField(verbose_name='Data')
    hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Godziny')
    description = models.TextField(verbose_name='Opis')
    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timesheets',
        verbose_name='Zadanie',
    )
    is_approved = models.BooleanField(default=False, verbose_name='Zatwierdzone')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_timesheets',
        verbose_name='Zatwierdzone przez',
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Data zatwierdzenia')
    rejection_reason = models.TextField(null=True, blank=True, verbose_name='Powód odrzucenia')
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_timesheets',
        verbose_name='Odrzucone przez',
    )
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name='Data odrzucenia')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data utworzenia')

    @property
    def approval_status(self):
        if self.is_approved:
            return 'approved'
        if self.rejected_by_id:
            return 'rejected'
        return 'pending'

    class Meta:
        verbose_name = 'wpis czasu pracy'
        verbose_name_plural = 'wpisy czasu pracy'
        ordering = ['-date']

    def __str__(self):
        return f'{self.user} — {self.date} ({self.hours}h)'

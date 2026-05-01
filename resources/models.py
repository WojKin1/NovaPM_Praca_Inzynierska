from decimal import Decimal

from django.conf import settings
from django.db import models

from projects.models import Project


class ProjectMember(models.Model):
    class RoleInProject(models.TextChoices):
        PM = 'PM', 'Project Manager'
        ANALYST = 'ANALYST', 'Analityk'
        DEVELOPER = 'DEVELOPER', 'Programista'
        TESTER = 'TESTER', 'Tester'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members', verbose_name='Projekt')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='project_memberships',
        verbose_name='Użytkownik',
    )
    role_in_project = models.CharField(max_length=15, choices=RoleInProject.choices, verbose_name='Rola w projekcie')
    availability_percent = models.IntegerField(default=100, verbose_name='Dostępność (%)')
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Stawka godzinowa')
    joined_at = models.DateField(auto_now_add=True, verbose_name='Data dołączenia')
    is_active = models.BooleanField(default=True, verbose_name='Aktywny')

    @property
    def effective_rate(self):
        if self.hourly_rate is not None:
            return self.hourly_rate
        from accounts.models import HOURLY_RATES
        return HOURLY_RATES.get(self.user.role, Decimal('0.00'))

    class Meta:
        verbose_name = 'członka zespołu'
        verbose_name_plural = 'członkowie zespołu'
        unique_together = [('project', 'user')]
        ordering = ['project', 'user']

    def __str__(self):
        return f'{self.user} — {self.project} ({self.get_role_in_project_display()})'

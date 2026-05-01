from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        PM = 'PM', 'Project Manager'
        ANALYST = 'ANALYST', 'Analityk biznesowy'
        DEVELOPER = 'DEVELOPER', 'Developer'
        TESTER = 'TESTER', 'Tester/QA'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DEVELOPER,
        verbose_name='Rola',
    )
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='Telefon')
    is_active_employee = models.BooleanField(default=True, verbose_name='Aktywny pracownik')
    must_change_password = models.BooleanField(default=False, verbose_name='Wymagana zmiana hasła')

    class Meta(AbstractUser.Meta):
        verbose_name = 'użytkownika'
        verbose_name_plural = 'użytkownicy'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


HOURLY_RATES = {
    User.Role.PM:        Decimal('200.00'),
    User.Role.ANALYST:   Decimal('180.00'),
    User.Role.DEVELOPER: Decimal('150.00'),
    User.Role.TESTER:    Decimal('120.00'),
    User.Role.ADMIN:     Decimal('0.00'),
}

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Testuje konfigurację SMTP przez wysłanie wiadomości testowej'

    def add_arguments(self, parser):
        parser.add_argument('to_email', type=str, help='Adres odbiorcy')

    def handle(self, *args, **options):
        to = options['to_email']
        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'Host:    {getattr(settings, "EMAIL_HOST", "—")}')
        self.stdout.write(f'Port:    {getattr(settings, "EMAIL_PORT", "—")}')
        self.stdout.write(f'User:    {getattr(settings, "EMAIL_HOST_USER", "—")}')
        self.stdout.write(f'From:    {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'Do:      {to}')
        self.stdout.write('')
        try:
            send_mail(
                subject='Test emaila — NovaPM',
                message='Ten email potwierdza, że konfiguracja SMTP działa poprawnie.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to],
            )
            self.stdout.write(self.style.SUCCESS(f'Email wysłany do {to}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Błąd: {exc}'))

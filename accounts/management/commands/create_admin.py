from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = 'Tworzy konto administratora (jednorazowe, bezpieczne)'

    def handle(self, *args, **kwargs):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='wk305371@student.polsl.pl',
                password='Admin1234!',
                role=User.Role.ADMIN,
                must_change_password=True,
            )
            self.stdout.write(self.style.SUCCESS('Admin utworzony'))
        else:
            self.stdout.write('Admin już istnieje — pomijam')

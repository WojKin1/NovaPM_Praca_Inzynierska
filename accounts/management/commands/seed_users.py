from django.core.management.base import BaseCommand

from accounts.models import User

SEED_USERS = [
    {'username': 'pm_test',      'role': User.Role.PM,        'password': 'Test1234!'},
    {'username': 'dev_test',     'role': User.Role.DEVELOPER,  'password': 'Test1234!'},
    {'username': 'analyst_test', 'role': User.Role.ANALYST,    'password': 'Test1234!'},
    {'username': 'tester_test',  'role': User.Role.TESTER,     'password': 'Test1234!'},
]


class Command(BaseCommand):
    help = 'Tworzy testowych użytkowników (jeśli nie istnieją)'

    def handle(self, *args, **options):
        created, skipped = 0, 0
        for data in SEED_USERS:
            user, was_created = User.objects.get_or_create(
                username=data['username'],
                defaults={'role': data['role']},
            )
            if was_created:
                user.set_password(data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  Utworzono: {data['username']} ({data['role']})"
                ))
                created += 1
            else:
                self.stdout.write(f"  Pominięto (już istnieje): {data['username']}")
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nGotowe — utworzono: {created}, pominięto: {skipped}'
        ))

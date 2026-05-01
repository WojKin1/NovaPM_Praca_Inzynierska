"""
Seed produkcyjnych danych testowych — idempotentny (get_or_create wszędzie).
"""
from decimal import Decimal
from datetime import date, datetime, timezone

from django.core.management.base import BaseCommand

from accounts.models import User
from budget.models import BudgetCategory, Timesheet
from changes.models import ChangeRequest
from projects.models import Project
from requirements_wbs.models import Requirement, WBSElement
from resources.models import ProjectMember
from risks.models import Risk
from tasks.models import Task, TaskReview


class Command(BaseCommand):
    help = 'Tworzy produkcyjne dane testowe (idempotentny)'

    def handle(self, *args, **kwargs):
        self.stdout.write('=== seed_production start ===')

        # ── 1. Użytkownicy ────────────────────────────────────────────────────
        admin = self._user('admin', 'admin123', User.Role.ADMIN,
                           email='wk305371@student.polsl.pl',
                           first_name='Admin', last_name='NovaPM',
                           is_staff=True, is_superuser=True,
                           must_change_password=False)
        pm = self._user('pm_test', 'Test1234!', User.Role.PM,
                        email='wk305371@student.polsl.pl',
                        first_name='Jan', last_name='Kowalski',
                        must_change_password=False)
        dev = self._user('dev_test', 'Test1234!', User.Role.DEVELOPER,
                         email='dev_test@novapm.local',
                         first_name='Marek', last_name='Nowak',
                         must_change_password=False)
        analyst = self._user('analyst_test', 'Test1234!', User.Role.ANALYST,
                             email='analyst_test@novapm.local',
                             first_name='Anna', last_name='Wiśniewska',
                             must_change_password=False)
        tester = self._user('tester_test', 'Test1234!', User.Role.TESTER,
                            email='tester_test@novapm.local',
                            first_name='Piotr', last_name='Zając',
                            must_change_password=False)

        # ── 2. Projekty ───────────────────────────────────────────────────────
        erp, _ = Project.objects.get_or_create(
            name='System ERP dla TechCorp',
            defaults=dict(
                description='Wdrożenie systemu ERP obejmującego moduły HR, finanse i logistykę.',
                client_name='TechCorp Sp. z o.o.',
                status=Project.Status.MONITORING,
                priority=Project.Priority.HIGH,
                start_date=date(2026, 1, 15),
                end_date=date(2026, 6, 30),
                budget_planned=Decimal('450000.00'),
                project_manager=pm,
                created_by=pm,
            ),
        )
        self.stdout.write(f'  Projekt: {erp.name}')

        Project.objects.get_or_create(
            name='Portal klienta - BankPlus',
            defaults=dict(
                client_name='BankPlus S.A.',
                status=Project.Status.PLANNING,
                priority=Project.Priority.CRITICAL,
                start_date=date(2026, 3, 1),
                end_date=date(2026, 8, 31),
                budget_planned=Decimal('320000.00'),
                project_manager=pm,
                created_by=pm,
            ),
        )

        Project.objects.get_or_create(
            name='Migracja infrastruktury - CloudMove',
            defaults=dict(
                client_name='CloudMove Sp. k.',
                status=Project.Status.CLOSED,
                priority=Project.Priority.MEDIUM,
                start_date=date(2025, 9, 1),
                end_date=date(2026, 2, 28),
                budget_planned=Decimal('180000.00'),
                project_manager=pm,
                created_by=pm,
            ),
        )

        # ── 3. Członkowie zespołu ─────────────────────────────────────────────
        self._member(erp, pm,      'PM',        100, Decimal('200.00'))
        self._member(erp, dev,     'DEVELOPER',  80, Decimal('150.00'))
        self._member(erp, analyst, 'ANALYST',    50, Decimal('180.00'))
        self._member(erp, tester,  'TESTER',    100, Decimal('120.00'))

        # ── 4. Zadania ────────────────────────────────────────────────────────
        t_hr = self._task(erp, 'Implementacja modułu HR',
                          'TODO', 'CRITICAL', date(2026, 9, 30), 120, dev, pm)
        t_arch = self._task(erp, 'Projekt architektury systemu',
                            'IN_PROGRESS', 'HIGH', date(2026, 6, 15), 40, dev, pm)
        t_anal = self._task(erp, 'Analiza wymagań biznesowych',
                            'DONE', 'HIGH', date(2026, 4, 30), 60, analyst, pm)
        t_test = self._task(erp, 'Testy integracyjne modułu HR',
                            'IN_REVIEW', 'MEDIUM', date(2026, 7, 15), 30, tester, pm)
        t_doc = self._task(erp, 'Dokumentacja API',
                           'IN_PROGRESS', 'LOW', date(2026, 8, 1), 20, dev, pm)

        # ── 5. Task Review ────────────────────────────────────────────────────
        if not TaskReview.objects.filter(task=t_test, reviewer=tester).exists():
            TaskReview.objects.create(
                task=t_test,
                reviewer=tester,
                result='REJECTED',
                comment='Brak walidacji formularza logowania - pole email nie sprawdza poprawności formatu',
            )
            self.stdout.write('  TaskReview: dodano odrzucenie dla t_test')

        # ── 6. Ryzyka ─────────────────────────────────────────────────────────
        self._risk(erp, 'Opóźnienie dostawy licencji',
                   4, 4, 'ANALYSED', pm,
                   'Negocjacje z dostawcą, alternatywne licencje open-source')
        self._risk(erp, 'Rotacja kluczowych developerów',
                   3, 5, 'IDENTIFIED', pm,
                   'Dokumentacja kodu, knowledge sharing sessions')
        self._risk(erp, 'Przekroczenie budżetu',
                   2, 4, 'IDENTIFIED', pm,
                   'Cotygodniowy monitoring kosztów, bufor 10%')

        # ── 7. Wnioski o zmianę ───────────────────────────────────────────────
        self._cr(erp, 'Rozszerzenie modułu raportów', 'APPROVED',
                 analyst, pm,
                 'Dodanie 5 nowych typów raportów', 14, Decimal('25000.00'),
                 'Zaakceptowano - mieści się w budżecie')
        self._cr(erp, 'Zmiana technologii frontendu', 'REJECTED',
                 dev, pm,
                 'Migracja z Django templates na React', 30, Decimal('45000.00'),
                 'Odrzucono - zbyt duże ryzyko opóźnienia')
        self._cr(erp, 'Dodanie modułu powiadomień email', 'SUBMITTED',
                 dev, None,
                 'Automatyczne powiadomienia email dla użytkowników', 7, Decimal('8000.00'),
                 '')

        # ── 8. Budżet ─────────────────────────────────────────────────────────
        BudgetCategory.objects.get_or_create(
            project=erp,
            category_type='INFRASTRUCTURE',
            defaults=dict(
                name='Serwery AWS',
                planned_amount=Decimal('50000.00'),
                spent_amount=Decimal('12000.00'),
            ),
        )
        BudgetCategory.objects.get_or_create(
            project=erp,
            category_type='LICENSES',
            defaults=dict(
                name='Licencje oprogramowania',
                planned_amount=Decimal('30000.00'),
                spent_amount=Decimal('8500.00'),
            ),
        )

        # ── 9. Timesheet ──────────────────────────────────────────────────────
        entries = [
            (date(2026, 4, 24), Decimal('6'), 'Analiza wymagań',       t_anal, True),
            (date(2026, 4, 23), Decimal('4'), 'Projekt architektury',  t_arch, True),
            (date(2026, 4, 22), Decimal('3'), 'Implementacja HR',      t_hr,   False),
            (date(2026, 4, 21), Decimal('8'), 'Analiza wymagań',       t_anal, True),
            (date(2026, 4, 17), Decimal('5'), 'Testy',                 t_test, False),
            (date(2026, 4, 16), Decimal('2'), 'Projekt architektury',  t_arch, True),
        ]
        for entry_date, hours, desc, task, approved in entries:
            ts, created = Timesheet.objects.get_or_create(
                project=erp,
                user=dev,
                date=entry_date,
                defaults=dict(
                    hours=hours,
                    description=desc,
                    task=task,
                    is_approved=approved,
                    approved_by=pm if approved else None,
                    approved_at=datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc) if approved else None,
                ),
            )
            if created:
                self.stdout.write(f'  Timesheet: {entry_date} {hours}h')

        # ── 10. Wymagania ─────────────────────────────────────────────────────
        reqs = [
            ('REQ-001', 'Logowanie użytkownika',           'FUNCTIONAL',     'HIGH',   'APPROVED'),
            ('REQ-002', 'Zarządzanie kontrahentami',        'FUNCTIONAL',     'HIGH',   'IMPLEMENTED'),
            ('REQ-003', 'Wystawianie faktur',               'FUNCTIONAL',     'MEDIUM', 'APPROVED'),
            ('REQ-004', 'Raporty miesięczne',               'FUNCTIONAL',     'MEDIUM', 'DRAFT'),
            ('REQ-005', 'Wydajność - max 2s odpowiedzi',    'NON_FUNCTIONAL', 'HIGH',   'APPROVED'),
            ('REQ-006', 'RODO compliance',                  'NON_FUNCTIONAL', 'HIGH',   'IMPLEMENTED'),
            ('REQ-007', 'Dostępność 99.9%',                 'NON_FUNCTIONAL', 'MEDIUM', 'DRAFT'),
            ('REQ-008', 'Eksport do CSV',                   'FUNCTIONAL',     'LOW',    'REJECTED'),
        ]
        for code, title, rtype, priority, status in reqs:
            Requirement.objects.get_or_create(
                project=erp,
                code=code,
                defaults=dict(
                    title=title,
                    req_type=rtype,
                    priority=priority,
                    status=status,
                    created_by=analyst,
                ),
            )
        self.stdout.write(f'  Wymagania: {len(reqs)} szt.')

        # ── 11. WBS ───────────────────────────────────────────────────────────
        wbs_structure = [
            ('1',   'Moduł HR',              None,  0, [
                ('1.1', 'Zarządzanie pracownikami', 0),
                ('1.2', 'Urlopy i nieobecności',    1),
                ('1.3', 'Lista płac',               2),
            ]),
            ('2',   'Moduł Finanse',         None,  1, [
                ('2.1', 'Faktury',           0),
                ('2.2', 'Raporty finansowe', 1),
            ]),
            ('3',   'Moduł Logistyka',       None,  2, [
                ('3.1', 'Magazyn',  0),
                ('3.2', 'Wysyłki',  1),
            ]),
        ]
        for code, name, _, order, children in wbs_structure:
            parent, _ = WBSElement.objects.get_or_create(
                project=erp, code=code,
                defaults=dict(name=name, order=order),
            )
            for child_code, child_name, child_order in children:
                WBSElement.objects.get_or_create(
                    project=erp, code=child_code,
                    defaults=dict(name=child_name, order=child_order, parent=parent),
                )
        self.stdout.write('  WBS: 3 moduły + 7 elementów')

        self.stdout.write(self.style.SUCCESS('=== seed_production OK ==='))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _user(self, username, password, role, email='', first_name='',
              last_name='', is_staff=False, is_superuser=False,
              must_change_password=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults=dict(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_staff=is_staff,
                is_superuser=is_superuser,
                must_change_password=must_change_password,
            ),
        )
        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(f'  Użytkownik: {username} (nowy)')
        else:
            self.stdout.write(f'  Użytkownik: {username} (istnieje)')
        return user

    def _member(self, project, user, role, availability, hourly_rate):
        ProjectMember.objects.get_or_create(
            project=project,
            user=user,
            defaults=dict(
                role_in_project=role,
                availability_percent=availability,
                hourly_rate=hourly_rate,
            ),
        )

    def _task(self, project, title, status, priority, due_date,
              estimated_hours, assigned_to, created_by):
        task, created = Task.objects.get_or_create(
            project=project,
            title=title,
            defaults=dict(
                status=status,
                priority=priority,
                due_date=due_date,
                estimated_hours=Decimal(str(estimated_hours)),
                assigned_to=assigned_to,
                created_by=created_by,
            ),
        )
        if created:
            self.stdout.write(f'  Zadanie: {title}')
        return task

    def _risk(self, project, title, probability, impact, status, owner, mitigation):
        Risk.objects.get_or_create(
            project=project,
            title=title,
            defaults=dict(
                probability=probability,
                impact=impact,
                status=status,
                owner=owner,
                mitigation_plan=mitigation,
            ),
        )

    def _cr(self, project, title, status, requested_by, decision_by,
            impact_scope, impact_time, impact_cost, decision_notes):
        ChangeRequest.objects.get_or_create(
            project=project,
            title=title,
            defaults=dict(
                description=decision_notes or impact_scope,
                status=status,
                requested_by=requested_by,
                decision_by=decision_by,
                decision_date=date(2026, 4, 20) if decision_by else None,
                impact_scope=impact_scope,
                impact_time=impact_time,
                impact_cost=impact_cost,
            ),
        )

from decimal import Decimal

from django.db.models import Sum

from accounts.models import HOURLY_RATES, User
from .models import BudgetCategory, Timesheet


def _get_member_rate(user, project):
    from resources.models import ProjectMember
    try:
        member = ProjectMember.objects.get(project=project, user=user)
        return member.effective_rate
    except ProjectMember.DoesNotExist:
        return HOURLY_RATES.get(user.role, Decimal('0.00'))


def recalculate_labour_budget(project):
    timesheets = (
        Timesheet.objects.filter(project=project, is_approved=True)
        .select_related('user')
    )
    total_cost = Decimal('0.00')
    for ts in timesheets:
        rate = _get_member_rate(ts.user, project)
        total_cost += ts.hours * rate

    labour_cats = BudgetCategory.objects.filter(
        project=project,
        category_type=BudgetCategory.CategoryType.LABOUR,
    ).order_by('id')

    count = labour_cats.count()
    if count > 1:
        first = labour_cats.first()
        labour_cats.exclude(pk=first.pk).delete()
        labour_cat = first
    elif count == 1:
        labour_cat = labour_cats.first()
    else:
        labour_cat = BudgetCategory.objects.create(
            project=project,
            category_type=BudgetCategory.CategoryType.LABOUR,
            name='Praca zespołu',
            planned_amount=Decimal('0.00'),
            spent_amount=Decimal('0.00'),
        )

    if labour_cat.spent_amount != total_cost:
        labour_cat.spent_amount = total_cost
        labour_cat.save(update_fields=['spent_amount'])

    return total_cost


def recalculate_project_spent(project):
    total = (
        project.budget_categories.aggregate(s=Sum('spent_amount'))['s']
        or Decimal('0.00')
    )
    project.budget_spent = total
    project.save(update_fields=['budget_spent'])


def get_labour_breakdown(project):
    from resources.models import ProjectMember

    rows = (
        Timesheet.objects.filter(project=project, is_approved=True)
        .select_related('user')
        .values(
            'user_id',
            'user__username',
            'user__first_name',
            'user__last_name',
            'user__role',
        )
        .annotate(total_hours=Sum('hours'))
        .order_by('user__username')
    )

    member_rates = {
        m.user_id: m.effective_rate
        for m in ProjectMember.objects.filter(project=project).select_related('user')
    }

    role_labels = dict(User.Role.choices)
    result = []
    for row in rows:
        role  = row['user__role']
        rate  = member_rates.get(row['user_id'], HOURLY_RATES.get(role, Decimal('0.00')))
        hours = row['total_hours']
        fn    = row['user__first_name']
        ln    = row['user__last_name']
        result.append({
            'username':     row['user__username'],
            'full_name':    f'{fn} {ln}'.strip() or row['user__username'],
            'role':         role,
            'role_display': role_labels.get(role, role),
            'hours':        hours,
            'rate':         rate,
            'cost':         hours * rate,
        })
    return result

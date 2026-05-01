from django.db.models import Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import BudgetCategory, Timesheet


def _sync_actual_hours(task):
    if task is None:
        return
    total = (
        Timesheet.objects.filter(task=task, is_approved=True)
        .aggregate(h=Sum('hours'))['h'] or 0
    )
    task.actual_hours = total
    task.save(update_fields=['actual_hours'])


def _recalc(project):
    from .services import recalculate_labour_budget, recalculate_project_spent
    recalculate_labour_budget(project)
    recalculate_project_spent(project)


@receiver(post_save, sender=Timesheet)
def timesheet_saved(sender, instance, **kwargs):
    _sync_actual_hours(instance.task)
    _recalc(instance.project)


@receiver(post_delete, sender=Timesheet)
def timesheet_deleted(sender, instance, **kwargs):
    _sync_actual_hours(instance.task)
    _recalc(instance.project)


@receiver(post_save, sender=BudgetCategory)
def budget_category_saved(sender, instance, **kwargs):
    # Skip if called during recalculate_labour_budget to avoid cascade loop
    update_fields = kwargs.get('update_fields')
    if update_fields and set(update_fields) == {'spent_amount'}:
        from .services import recalculate_project_spent
        recalculate_project_spent(instance.project)
        return
    if update_fields is None or 'spent_amount' not in (update_fields or []):
        from .services import recalculate_project_spent
        recalculate_project_spent(instance.project)


@receiver(post_delete, sender=BudgetCategory)
def budget_category_deleted(sender, instance, **kwargs):
    from .services import recalculate_project_spent
    recalculate_project_spent(instance.project)

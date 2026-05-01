from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ProjectMember


def _recalc(project):
    from budget.services import recalculate_labour_budget, recalculate_project_spent
    recalculate_labour_budget(project)
    recalculate_project_spent(project)


@receiver(post_save, sender=ProjectMember)
def project_member_saved(sender, instance, **kwargs):
    _recalc(instance.project)


@receiver(post_delete, sender=ProjectMember)
def project_member_deleted(sender, instance, **kwargs):
    _recalc(instance.project)

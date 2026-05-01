from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from budget.models import Timesheet
from projects.models import Project
from .forms import MemberRateForm, ProjectMemberForm
from .models import ProjectMember


def _require_pm_or_staff(request, project):
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied


@login_required
def member_add(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_staff(request, project)

    if request.method == 'POST':
        form = ProjectMemberForm(request.POST, project=project)
        if form.is_valid():
            member = form.save(commit=False)
            member.project = project
            member.save()
            return redirect('project_detail', pk=project_pk)
    else:
        form = ProjectMemberForm(project=project)

    return render(request, 'resources/member_form.html', {
        'form':    form,
        'project': project,
    })


@login_required
def member_remove(request, project_pk, member_pk):
    if request.method != 'POST':
        return redirect('project_detail', pk=project_pk)

    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_staff(request, project)

    member = get_object_or_404(ProjectMember, pk=member_pk, project=project)
    member.is_active = False
    member.save()
    return redirect('project_detail', pk=project_pk)


@login_required
def project_team_rates(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_staff(request, project)

    members = (
        ProjectMember.objects.filter(project=project, is_active=True)
        .select_related('user')
        .order_by('user__username')
    )

    approved_hours_map = {
        row['user_id']: row['total_hours']
        for row in Timesheet.objects.filter(project=project, is_approved=True)
        .values('user_id')
        .annotate(total_hours=Sum('hours'))
    }

    rows = []
    total_cost = Decimal('0.00')
    for m in members:
        hours = approved_hours_map.get(m.user_id, Decimal('0'))
        rate = m.effective_rate
        cost = hours * rate
        total_cost += cost
        rows.append({
            'member':      m,
            'hours':       hours,
            'rate':        rate,
            'cost':        cost,
            'is_custom':   m.hourly_rate is not None,
        })

    return render(request, 'resources/team_rates.html', {
        'project':    project,
        'rows':       rows,
        'total_cost': total_cost,
    })


@login_required
def member_edit_rate(request, project_pk, member_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_staff(request, project)
    member = get_object_or_404(ProjectMember, pk=member_pk, project=project)

    if request.method == 'POST':
        form = MemberRateForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            from budget.services import recalculate_labour_budget, recalculate_project_spent
            recalculate_labour_budget(project)
            recalculate_project_spent(project)
            return redirect('project_team_rates', project_pk=project_pk)
    else:
        form = MemberRateForm(instance=member)

    return render(request, 'resources/member_rate_form.html', {
        'form':    form,
        'project': project,
        'member':  member,
    })

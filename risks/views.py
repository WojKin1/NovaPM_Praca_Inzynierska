from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from projects.models import Project
from resources.models import ProjectMember
from .forms import RiskForm
from .models import Risk


def _can_view(request, project):
    """PM, staff or active project member may view."""
    if project.project_manager == request.user or request.user.is_staff:
        return True
    return ProjectMember.objects.filter(
        project=project, user=request.user, is_active=True
    ).exists()


def _require_pm_or_staff(request, project):
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied


def _require_pm_or_analyst(request, project):
    if project.project_manager == request.user or request.user.is_staff:
        return
    member = ProjectMember.objects.filter(
        project=project, user=request.user, is_active=True
    ).first()
    if member and getattr(request.user, 'role', None) == 'ANALYST':
        return
    raise PermissionDenied


@login_required
def risk_list(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _can_view(request, project):
        raise PermissionDenied

    risks = project.risks.select_related('owner').order_by('status', '-probability', '-impact')

    grouped = {
        'IDENTIFIED': risks.filter(status=Risk.Status.IDENTIFIED),
        'ANALYSED':   risks.filter(status=Risk.Status.ANALYSED),
        'MITIGATED':  risks.filter(status=Risk.Status.MITIGATED),
        'CLOSED':     risks.filter(status=Risk.Status.CLOSED),
    }

    # Build matrix data: list of (probability, impact, risk) for active risks
    active_risks = risks.exclude(status=Risk.Status.CLOSED)
    matrix_dots = [
        {'p': r.probability, 'i': r.impact, 'title': r.title, 'level': r.risk_level}
        for r in active_risks
    ]

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_analyst = getattr(request.user, 'role', None) == 'ANALYST' and ProjectMember.objects.filter(
        project=project, user=request.user, is_active=True
    ).exists()

    return render(request, 'risks/risk_list.html', {
        'project':       project,
        'risks':         risks,
        'grouped':       grouped,
        'matrix_dots':   matrix_dots,
        'is_pm_or_staff': is_pm_or_staff,
        'is_analyst':    is_analyst,
    })


@login_required
def risk_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_analyst(request, project)

    if request.method == 'POST':
        form = RiskForm(request.POST)
        if form.is_valid():
            risk = form.save(commit=False)
            risk.project = project
            risk.save()
            return redirect('risk_list', project_pk=project_pk)
    else:
        form = RiskForm()

    return render(request, 'risks/risk_form.html', {'form': form, 'project': project, 'risk': None})


@login_required
def risk_edit(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_analyst(request, project)
    risk = get_object_or_404(Risk, pk=pk, project=project)

    if request.method == 'POST':
        form = RiskForm(request.POST, instance=risk)
        if form.is_valid():
            form.save()
            return redirect('risk_list', project_pk=project_pk)
    else:
        form = RiskForm(instance=risk)

    return render(request, 'risks/risk_form.html', {'form': form, 'project': project, 'risk': risk})


@login_required
def risk_close(request, project_pk, pk):
    if request.method != 'POST':
        return redirect('risk_list', project_pk=project_pk)

    project = get_object_or_404(Project, pk=project_pk)
    _require_pm_or_staff(request, project)
    risk = get_object_or_404(Risk, pk=pk, project=project)
    risk.status = Risk.Status.CLOSED
    risk.save(update_fields=['status', 'updated_at'])
    return redirect('risk_list', project_pk=project_pk)

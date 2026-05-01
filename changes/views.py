from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from projects.models import Project
from resources.models import ProjectMember
from .forms import ChangeRequestForm, DecisionForm
from .models import ChangeRequest


@login_required
def cr_select_project(request):
    member_qs = ProjectMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('project')

    projects = [m.project for m in member_qs]

    if len(projects) == 1:
        return redirect('cr_create', project_pk=projects[0].pk)

    return render(request, 'changes/cr_select_project.html', {
        'projects': projects,
    })


def _is_member(request, project):
    if project.project_manager == request.user or request.user.is_staff:
        return True
    return ProjectMember.objects.filter(
        project=project, user=request.user, is_active=True
    ).exists()


def _require_member(request, project):
    if not _is_member(request, project):
        raise PermissionDenied


def _require_pm_or_staff(request, project):
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied


@login_required
def cr_list(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_member(request, project)

    status_filter = request.GET.get('status', '')
    qs = project.change_requests.select_related('requested_by', 'decision_by').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)

    return render(request, 'changes/cr_list.html', {
        'project':       project,
        'crs':           qs,
        'status_filter': status_filter,
        'statuses':      ChangeRequest.Status.choices,
        'is_pm_or_staff': is_pm_or_staff,
        'can_create':    _is_member(request, project),
    })


@login_required
def cr_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_member(request, project)

    if request.method == 'POST':
        form = ChangeRequestForm(request.POST)
        if form.is_valid():
            cr = form.save(commit=False)
            cr.project = project
            cr.requested_by = request.user
            cr.save()
            return redirect('cr_detail', project_pk=project_pk, pk=cr.pk)
    else:
        form = ChangeRequestForm()

    return render(request, 'changes/cr_form.html', {'form': form, 'project': project})


@login_required
def cr_detail(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_member(request, project)
    cr = get_object_or_404(ChangeRequest, pk=pk, project=project)

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_author = (cr.requested_by == request.user)
    can_decide = is_pm_or_staff and cr.status in (
        ChangeRequest.Status.SUBMITTED, ChangeRequest.Status.ANALYSED
    )

    decision_form = None
    if can_decide:
        if request.method == 'POST':
            decision_form = DecisionForm(request.POST)
            if decision_form.is_valid():
                cr.status = decision_form.cleaned_data['status']
                cr.decision_by = request.user
                cr.decision_date = timezone.localdate()
                cr.save(update_fields=['status', 'decision_by', 'decision_date', 'updated_at'])
                return redirect('cr_detail', project_pk=project_pk, pk=pk)
        else:
            decision_form = DecisionForm()

    return render(request, 'changes/cr_detail.html', {
        'project':       project,
        'cr':            cr,
        'is_pm_or_staff': is_pm_or_staff,
        'is_author':     is_author,
        'can_decide':    can_decide,
        'decision_form': decision_form,
    })


@login_required
def cr_submit(request, project_pk, pk):
    if request.method != 'POST':
        return redirect('cr_detail', project_pk=project_pk, pk=pk)

    project = get_object_or_404(Project, pk=project_pk)
    cr = get_object_or_404(ChangeRequest, pk=pk, project=project)

    if cr.requested_by != request.user and not request.user.is_staff:
        raise PermissionDenied

    if cr.status == ChangeRequest.Status.DRAFT:
        cr.status = ChangeRequest.Status.SUBMITTED
        cr.save(update_fields=['status', 'updated_at'])

    return redirect('cr_detail', project_pk=project_pk, pk=pk)

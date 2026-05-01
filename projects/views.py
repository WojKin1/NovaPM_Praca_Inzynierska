from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from changes.models import ChangeRequest
from resources.models import ProjectMember
from risks.models import Risk
from tasks.models import Task

from accounts.models import User
from .forms import ProjectForm
from .models import Project


def _require_pm_or_staff(user):
    if not user.is_staff and getattr(user, 'role', None) != User.Role.PM:
        raise PermissionDenied


@login_required
def project_list(request):
    user = request.user
    if getattr(user, 'role', None) == User.Role.ANALYST:
        return redirect('my_requirements_projects')
    if getattr(user, 'role', None) in (User.Role.DEVELOPER, User.Role.TESTER):
        return redirect('my_tasks')
    _require_pm_or_staff(user)

    today = timezone.localdate()
    qs = Project.objects.filter(project_manager=request.user).select_related('project_manager')

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    overdue = Project.objects.filter(
        project_manager=request.user,
        end_date__lt=today,
    ).exclude(status=Project.Status.CLOSED)

    all_projects = Project.objects.filter(project_manager=request.user)
    stats = {
        'total':     all_projects.count(),
        'execution': all_projects.filter(status=Project.Status.EXECUTION).count(),
        'closed':    all_projects.filter(status=Project.Status.CLOSED).count(),
        'overdue':   overdue.count(),
    }

    return render(request, 'projects/project_list.html', {
        'projects':      qs,
        'stats':         stats,
        'status_filter': status_filter,
        'statuses':      Project.Status.choices,
        'today':         today,
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_member_qs = ProjectMember.objects.filter(
        project=project, user=request.user, is_active=True
    ).exists()
    is_member = is_pm_or_staff or is_member_qs

    if not is_member:
        raise PermissionDenied

    today = timezone.localdate()

    # Tasks
    tasks_qs = project.tasks.select_related('assigned_to').order_by('-created_at')
    task_total = tasks_qs.count()
    task_done  = tasks_qs.filter(status=Task.Status.DONE).count()
    task_pct   = round(task_done / task_total * 100) if task_total else 0

    task_counts = {
        'TODO':        tasks_qs.filter(status=Task.Status.TODO).count(),
        'IN_PROGRESS': tasks_qs.filter(status=Task.Status.IN_PROGRESS).count(),
        'IN_REVIEW':   tasks_qs.filter(status=Task.Status.IN_REVIEW).count(),
        'DONE':        task_done,
        'BLOCKED':     tasks_qs.filter(status=Task.Status.BLOCKED).count(),
    }

    recent_tasks = tasks_qs[:5]

    # Risks
    active_risks = project.risks.filter(
        status__in=[Risk.Status.IDENTIFIED, Risk.Status.ANALYSED]
    ).select_related('owner')

    # Change requests
    open_crs = project.change_requests.filter(
        status__in=[
            ChangeRequest.Status.DRAFT,
            ChangeRequest.Status.SUBMITTED,
            ChangeRequest.Status.ANALYSED,
        ]
    ).select_related('requested_by')

    # Team
    members = project.members.filter(is_active=True).select_related('user')

    # Budget
    budget_categories = project.budget_categories.all()
    budget_pct = (
        round(float(project.budget_spent) / float(project.budget_planned) * 100)
        if project.budget_planned else 0
    )
    budget_over = project.budget_spent > project.budget_planned

    days_left = (project.end_date - today).days

    return render(request, 'projects/project_detail.html', {
        'project':           project,
        'today':             today,
        'days_left':         days_left,
        'task_total':        task_total,
        'task_done':         task_done,
        'task_pct':          task_pct,
        'task_counts':       task_counts,
        'recent_tasks':      recent_tasks,
        'active_risks':      active_risks,
        'open_crs':          open_crs,
        'members':           members,
        'budget_categories': budget_categories,
        'budget_pct':        min(budget_pct, 100),
        'budget_pct_raw':    budget_pct,
        'budget_over':       budget_over,
        'is_pm_or_staff':    is_pm_or_staff,
        'is_member':         is_member,
    })


@login_required
def project_create(request):
    _require_pm_or_staff(request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.project_manager = request.user
            project.created_by = request.user
            project.save()
            ProjectMember.objects.get_or_create(
                project=project,
                user=request.user,
                defaults={
                    'role_in_project': ProjectMember.RoleInProject.PM,
                    'availability_percent': 100,
                    'is_active': True,
                },
            )
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form, 'project': None})


@login_required
def project_edit(request, pk):
    _require_pm_or_staff(request.user)
    project = get_object_or_404(Project, pk=pk)
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            updated = form.save()
            ProjectMember.objects.get_or_create(
                project=updated,
                user=updated.project_manager,
                defaults={
                    'role_in_project': ProjectMember.RoleInProject.PM,
                    'availability_percent': 100,
                    'is_active': True,
                },
            )
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {'form': form, 'project': project})


# Status progression: each status maps to the one next logical step
_NEXT_STATUS = {
    Project.Status.INITIATION: Project.Status.PLANNING,
    Project.Status.PLANNING:   Project.Status.EXECUTION,
    Project.Status.EXECUTION:  Project.Status.MONITORING,
    Project.Status.MONITORING: Project.Status.CLOSED,
}

_NEXT_STATUS_LABEL = {
    Project.Status.INITIATION: 'Przejdź do Planowania',
    Project.Status.PLANNING:   'Przejdź do Realizacji',
    Project.Status.EXECUTION:  'Przejdź do Monitorowania',
    Project.Status.MONITORING: 'Zamknij projekt',
}


@login_required
def project_change_status(request, pk):
    _require_pm_or_staff(request.user)
    if request.method != 'POST':
        return redirect('project_detail', pk=pk)

    project = get_object_or_404(Project, pk=pk)
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied

    next_status = _NEXT_STATUS.get(project.status)
    if next_status:
        project.status = next_status
        project.save(update_fields=['status', 'updated_at'])

    return redirect('project_detail', pk=pk)

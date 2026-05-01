import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from projects.models import Project
from resources.models import ProjectMember
from .forms import TaskForm, TaskStatusForm
from .models import Task, TaskReview


def _is_member(request, project):
    if project.project_manager == request.user or request.user.is_staff:
        return True
    return ProjectMember.objects.filter(
        project=project, user=request.user, is_active=True
    ).exists()


def _group_by_status(qs):
    return {
        'TODO':        qs.filter(status=Task.Status.TODO),
        'IN_PROGRESS': qs.filter(status=Task.Status.IN_PROGRESS),
        'IN_REVIEW':   qs.filter(status=Task.Status.IN_REVIEW),
        'DONE':        qs.filter(status=Task.Status.DONE),
        'BLOCKED':     qs.filter(status=Task.Status.BLOCKED),
    }


@login_required
def my_reviews(request):
    today = timezone.localdate()

    member_project_ids = ProjectMember.objects.filter(
        user=request.user, is_active=True
    ).values_list('project_id', flat=True)

    tasks = (
        Task.objects
        .filter(project_id__in=member_project_ids, status=Task.Status.IN_REVIEW)
        .select_related('project', 'assigned_to')
        .prefetch_related('reviews__reviewer')
        .order_by('updated_at')
    )

    reviewed_today = TaskReview.objects.filter(
        reviewer=request.user,
        created_at__date=today,
    ).count()

    stats = {
        'pending':       tasks.count(),
        'urgent':        tasks.filter(due_date__lt=today).count(),
        'reviewed_today': reviewed_today,
    }

    return render(request, 'tasks/my_reviews.html', {
        'tasks': tasks,
        'stats': stats,
        'today': today,
    })


@login_required
@require_POST
def task_review(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project = task.project

    if not _is_member(request, project):
        raise PermissionDenied

    result = request.POST.get('result', '').strip()
    comment = request.POST.get('comment', '').strip()

    valid = (TaskReview.Result.APPROVED, TaskReview.Result.REJECTED)
    if result not in valid:
        return redirect('my_reviews')

    if result == TaskReview.Result.REJECTED and not comment:
        return redirect('my_reviews')

    TaskReview.objects.create(
        task=task,
        reviewer=request.user,
        result=result,
        comment=comment,
    )

    task.status = Task.Status.DONE if result == TaskReview.Result.APPROVED else Task.Status.IN_PROGRESS
    task.save(update_fields=['status', 'updated_at'])

    return redirect('my_reviews')


@login_required
def my_tasks(request):
    today = timezone.localdate()
    qs = Task.objects.filter(assigned_to=request.user).select_related('project', 'assigned_to').prefetch_related('reviews')

    stats = {
        'total':       qs.count(),
        'in_progress': qs.filter(status=Task.Status.IN_PROGRESS).count(),
        'done':        qs.filter(status=Task.Status.DONE).count(),
        'overdue':     qs.exclude(status=Task.Status.DONE).filter(due_date__lt=today).count(),
    }

    return render(request, 'tasks/my_tasks.html', {
        'kanban':  _group_by_status(qs),
        'stats':   stats,
        'today':   today,
    })


@login_required
def project_tasks(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _is_member(request, project):
        raise PermissionDenied

    today = timezone.localdate()
    qs = project.tasks.select_related('assigned_to', 'project')

    assigned_filter = request.GET.get('assigned_to', '')
    if assigned_filter:
        qs = qs.filter(assigned_to_id=assigned_filter)

    members = ProjectMember.objects.filter(
        project=project, is_active=True
    ).select_related('user')

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)

    return render(request, 'tasks/project_tasks.html', {
        'project':        project,
        'kanban':         _group_by_status(qs),
        'members':        members,
        'assigned_filter': assigned_filter,
        'is_pm_or_staff': is_pm_or_staff,
        'today':          today,
    })


@login_required
def task_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied

    if request.method == 'POST':
        form = TaskForm(request.POST, project=project)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.created_by = request.user
            task.save()
            return redirect('project_tasks', pk=pk)
    else:
        form = TaskForm(project=project)

    return render(request, 'tasks/task_form.html', {
        'form':    form,
        'project': project,
        'task':    None,
    })


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project = task.project
    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_assignee = (task.assigned_to == request.user)

    if not is_pm_or_staff and not is_assignee:
        raise PermissionDenied

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        if is_pm_or_staff:
            form = TaskForm(request.POST, instance=task, project=project)
        else:
            form = TaskStatusForm(request.POST, initial={
                'status': task.status,
                'actual_hours': task.actual_hours,
            })

        if form.is_valid():
            if is_pm_or_staff:
                form.save()
            else:
                task.status = form.cleaned_data['status']
                task.actual_hours = form.cleaned_data['actual_hours']
                task.save(update_fields=['status', 'actual_hours', 'updated_at'])

            if next_url == 'my_tasks':
                return redirect('my_tasks')
            return redirect('project_tasks', pk=project.pk)
    else:
        if is_pm_or_staff:
            form = TaskForm(instance=task, project=project)
        else:
            form = TaskStatusForm(initial={
                'status': task.status,
                'actual_hours': task.actual_hours,
            })

    reviews = list(task.reviews.select_related('reviewer').all()[:10]) if task else []
    last_review = reviews[0] if reviews else None

    return render(request, 'tasks/task_form.html', {
        'form':          form,
        'project':       project,
        'task':          task,
        'is_pm_or_staff': is_pm_or_staff,
        'is_assigned':   is_assignee,
        'next_url':      next_url,
        'reviews':       reviews,
        'last_review':   last_review,
    })


@login_required
@require_POST
def task_quick_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project = task.project
    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_assignee = (task.assigned_to == request.user)

    if not is_pm_or_staff and not is_assignee:
        raise PermissionDenied

    new_status = request.POST.get('status', '').strip()
    valid_statuses = [s[0] for s in Task.Status.choices]
    if new_status in valid_statuses:
        task.status = new_status
        task.save(update_fields=['status', 'updated_at'])

    next_url = request.POST.get('next', '')
    if next_url == 'my_tasks':
        return redirect('my_tasks')
    return redirect('task_edit', pk=pk)


@login_required
@require_POST
def task_change_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    project = task.project
    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_assignee = (task.assigned_to == request.user)

    if not is_pm_or_staff and not is_assignee:
        return JsonResponse({'error': 'Brak uprawnień'}, status=403)

    try:
        data = json.loads(request.body)
        new_status = data.get('status')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Nieprawidłowe dane'}, status=400)

    valid_statuses = [s[0] for s in Task.Status.choices]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Nieprawidłowy status'}, status=400)

    task.status = new_status
    task.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'ok': True, 'status': new_status})

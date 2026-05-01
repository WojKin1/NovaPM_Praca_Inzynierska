from datetime import timedelta
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_POST

from accounts.models import User
from projects.models import Project
from resources.models import ProjectMember
from .forms import BudgetCategoryForm, RejectionForm, TimesheetForm
from .models import BudgetCategory, Timesheet
from .services import get_labour_breakdown, recalculate_labour_budget, recalculate_project_spent


def _week_start(d):
    return d - timedelta(days=d.weekday())


def _auto_approve_if_pm(ts):
    if ts.user.is_staff or getattr(ts.user, 'role', None) == User.Role.PM:
        ts.is_approved = True
        ts.approved_by = ts.user
        ts.approved_at = timezone.now()
        ts.save(update_fields=['is_approved', 'approved_by', 'approved_at'])


@login_required
def my_timesheet(request):
    today = timezone.localdate()
    week_start = _week_start(today)
    month_start = today.replace(day=1)

    qs = Timesheet.objects.filter(user=request.user).select_related(
        'project', 'task', 'approved_by', 'rejected_by'
    ).order_by('-date', '-created_at')

    stats = {
        'week':   qs.filter(date__gte=week_start).aggregate(h=Sum('hours'))['h'] or 0,
        'month':  qs.filter(date__gte=month_start).aggregate(h=Sum('hours'))['h'] or 0,
        'total':  qs.aggregate(h=Sum('hours'))['h'] or 0,
        'tasks':  qs.filter(task__isnull=False).values('task').distinct().count(),
    }

    cutoff = week_start - timedelta(weeks=7)
    recent = list(qs.filter(date__gte=cutoff))

    weeks = []
    for ws, entries in groupby(recent, lambda ts: _week_start(ts.date)):
        entries_list = list(entries)
        we = ws + timedelta(days=6)
        weeks.append({
            'start': ws,
            'end':   we,
            'entries': entries_list,
            'total_hours': sum(e.hours for e in entries_list),
        })

    older = list(qs.filter(date__lt=cutoff))

    return render(request, 'budget/my_timesheet.html', {
        'weeks':   weeks,
        'older':   older,
        'stats':   stats,
        'today':   today,
    })


@login_required
def timesheet_add(request):
    today = timezone.localdate()

    member_project_ids = ProjectMember.objects.filter(
        user=request.user, is_active=True
    ).values_list('project_id', flat=True)
    projects = Project.objects.filter(pk__in=member_project_ids).order_by('name')

    project = None
    project_id = request.GET.get('project') or request.POST.get('project')
    if project_id:
        project = get_object_or_404(Project, pk=project_id)
        if not ProjectMember.objects.filter(
            project=project, user=request.user, is_active=True
        ).exists():
            raise PermissionDenied

    if request.method == 'POST' and project:
        form = TimesheetForm(request.POST, user=request.user, project=project)
        if form.is_valid():
            ts = form.save(commit=False)
            ts.user = request.user
            ts.project = project
            ts.save()
            _auto_approve_if_pm(ts)
            return redirect('my_timesheet')
    elif project:
        form = TimesheetForm(initial={'date': today}, user=request.user, project=project)
    else:
        form = None

    week_start = _week_start(today)
    week_hours = Timesheet.objects.filter(
        user=request.user, date__gte=week_start
    ).aggregate(h=Sum('hours'))['h'] or 0

    return render(request, 'budget/timesheet_form.html', {
        'form':       form,
        'project':    project,
        'projects':   projects,
        'week_hours': week_hours,
        'entry':      None,
        'today':      today,
    })


@login_required
def timesheet_edit(request, pk):
    ts = get_object_or_404(Timesheet, pk=pk)
    if ts.user != request.user:
        raise PermissionDenied

    is_pm = ts.user.is_staff or getattr(ts.user, 'role', None) == User.Role.PM
    if ts.is_approved and not is_pm:
        messages.error(request, 'Nie można edytować zatwierdzonego wpisu.')
        return redirect('my_timesheet')

    today = timezone.localdate()
    project = ts.project

    if request.method == 'POST':
        form = TimesheetForm(request.POST, instance=ts, user=request.user, project=project)
        if form.is_valid():
            updated = form.save(commit=False)
            # After edit, clear rejection state → back to PENDING
            updated.rejected_by = None
            updated.rejected_at = None
            updated.rejection_reason = ''
            updated.save()
            _auto_approve_if_pm(updated)
            return redirect('my_timesheet')
    else:
        form = TimesheetForm(instance=ts, user=request.user, project=project)

    week_start = _week_start(today)
    week_hours = Timesheet.objects.filter(
        user=request.user, date__gte=week_start
    ).exclude(pk=pk).aggregate(h=Sum('hours'))['h'] or 0

    return render(request, 'budget/timesheet_form.html', {
        'form':       form,
        'project':    project,
        'projects':   None,
        'week_hours': week_hours,
        'entry':      ts,
        'today':      today,
    })


@login_required
def timesheet_delete(request, pk):
    if request.method != 'POST':
        return redirect('my_timesheet')
    ts = get_object_or_404(Timesheet, pk=pk)
    if ts.user != request.user:
        raise PermissionDenied
    if ts.is_approved:
        messages.error(request, 'Nie można usunąć zatwierdzonego wpisu.')
        return redirect('my_timesheet')
    ts.delete()
    return redirect('my_timesheet')


# ─── PM views ────────────────────────────────────────────────────────────────

def _require_pm(request, project):
    if project.project_manager != request.user and not request.user.is_staff:
        raise PermissionDenied


@login_required
def project_timesheet(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_pm(request, project)

    status_filter = request.GET.get('status', '')

    qs = Timesheet.objects.filter(project=project).select_related(
        'user', 'task', 'approved_by', 'rejected_by'
    ).order_by('user__username', '-date')

    if status_filter == 'pending':
        qs = qs.filter(is_approved=False, rejected_by__isnull=True)
    elif status_filter == 'approved':
        qs = qs.filter(is_approved=True)
    elif status_filter == 'rejected':
        qs = qs.filter(is_approved=False, rejected_by__isnull=False)

    base_qs = Timesheet.objects.filter(project=project)
    stats = {
        'pending':   base_qs.filter(is_approved=False, rejected_by__isnull=True).aggregate(h=Sum('hours'))['h'] or 0,
        'approved':  base_qs.filter(is_approved=True).aggregate(h=Sum('hours'))['h'] or 0,
        'rejected':  base_qs.filter(is_approved=False, rejected_by__isnull=False).aggregate(h=Sum('hours'))['h'] or 0,
        'total':     base_qs.aggregate(h=Sum('hours'))['h'] or 0,
        'workers':   base_qs.values('user').distinct().count(),
    }

    grouped = []
    for user_obj, entries in groupby(qs, lambda ts: ts.user):
        entries_list = list(entries)
        approved_h = sum(e.hours for e in entries_list if e.is_approved)
        pending_h  = sum(e.hours for e in entries_list if not e.is_approved and not e.rejected_by_id)
        rejected_h = sum(e.hours for e in entries_list if not e.is_approved and e.rejected_by_id)
        grouped.append({
            'user':       user_obj,
            'entries':    entries_list,
            'approved_h': approved_h,
            'pending_h':  pending_h,
            'rejected_h': rejected_h,
        })

    return render(request, 'budget/project_timesheet.html', {
        'project':       project,
        'grouped':       grouped,
        'stats':         stats,
        'status_filter': status_filter,
    })


@login_required
@require_POST
def timesheet_approve(request, pk):
    ts = get_object_or_404(Timesheet, pk=pk)
    _require_pm(request, ts.project)
    ts.is_approved = True
    ts.approved_by = request.user
    ts.approved_at = timezone.now()
    ts.rejected_by = None
    ts.rejected_at = None
    ts.rejection_reason = ''
    ts.save(update_fields=[
        'is_approved', 'approved_by', 'approved_at',
        'rejected_by', 'rejected_at', 'rejection_reason',
    ])
    return redirect('project_timesheet', pk=ts.project.pk)


@login_required
def timesheet_reject(request, pk):
    ts = get_object_or_404(Timesheet, pk=pk)
    _require_pm(request, ts.project)

    if request.method == 'POST':
        form = RejectionForm(request.POST)
        if form.is_valid():
            ts.is_approved = False
            ts.approved_by = None
            ts.approved_at = None
            ts.rejected_by = request.user
            ts.rejected_at = timezone.now()
            ts.rejection_reason = form.cleaned_data['rejection_reason']
            ts.save(update_fields=[
                'is_approved', 'approved_by', 'approved_at',
                'rejected_by', 'rejected_at', 'rejection_reason',
            ])
            return redirect('project_timesheet', pk=ts.project.pk)
    else:
        form = RejectionForm()

    return render(request, 'budget/timesheet_reject_form.html', {
        'form':    form,
        'entry':   ts,
        'project': ts.project,
    })


@login_required
@require_POST
def timesheet_revoke_approval(request, pk):
    ts = get_object_or_404(Timesheet, pk=pk)
    _require_pm(request, ts.project)
    ts.is_approved = False
    ts.approved_by = None
    ts.approved_at = None
    ts.save(update_fields=['is_approved', 'approved_by', 'approved_at'])
    return redirect('project_timesheet', pk=ts.project.pk)


# ─── Budget views ─────────────────────────────────────────────────────────────

@login_required
def project_budget(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_pm(request, project)

    recalculate_labour_budget(project)
    recalculate_project_spent(project)
    project.refresh_from_db()

    categories = project.budget_categories.order_by('category_type', 'name')
    labour_cat  = categories.filter(category_type=BudgetCategory.CategoryType.LABOUR).first()
    other_cats  = categories.exclude(category_type=BudgetCategory.CategoryType.LABOUR)

    labour_breakdown = get_labour_breakdown(project)

    planned = project.budget_planned or 0
    spent   = project.budget_spent   or 0
    remaining = planned - spent
    budget_pct = round(float(spent) / float(planned) * 100) if planned else 0

    stats = {
        'planned':   planned,
        'spent':     spent,
        'remaining': remaining,
        'pct':       min(budget_pct, 100),
        'pct_raw':   budget_pct,
        'over':      spent > planned,
    }

    # Per-category pct for progress bars
    cats_with_pct = []
    for cat in other_cats:
        p = cat.planned_amount or 0
        s = cat.spent_amount or 0
        pct = round(float(s) / float(p) * 100) if p else 0
        cats_with_pct.append({
            'cat':     cat,
            'pct':     min(pct, 100),
            'pct_raw': pct,
            'over':    s > p,
        })

    return render(request, 'budget/project_budget.html', {
        'project':          project,
        'labour_cat':       labour_cat,
        'labour_breakdown': labour_breakdown,
        'cats_with_pct':    cats_with_pct,
        'stats':            stats,
    })


@login_required
def budget_category_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    _require_pm(request, project)

    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST, is_new=True)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.project = project
            cat.save()
            return redirect('project_budget', pk=pk)
    else:
        form = BudgetCategoryForm(is_new=True)

    return render(request, 'budget/category_form.html', {
        'form':      form,
        'project':   project,
        'category':  None,
        'is_labour': False,
    })


@login_required
def budget_category_edit(request, pk, cat_pk):
    project = get_object_or_404(Project, pk=pk)
    _require_pm(request, project)
    cat = get_object_or_404(BudgetCategory, pk=cat_pk, project=project)

    is_labour = (cat.category_type == BudgetCategory.CategoryType.LABOUR)

    if request.method == 'POST':
        form = BudgetCategoryForm(request.POST, instance=cat, is_labour=is_labour)
        if form.is_valid():
            form.save()
            return redirect('project_budget', pk=pk)
    else:
        form = BudgetCategoryForm(instance=cat, is_labour=is_labour)

    return render(request, 'budget/category_form.html', {
        'form':      form,
        'project':   project,
        'category':  cat,
        'is_labour': is_labour,
    })


@login_required
@require_POST
def budget_category_delete(request, pk, cat_pk):
    project = get_object_or_404(Project, pk=pk)
    _require_pm(request, project)
    cat = get_object_or_404(BudgetCategory, pk=cat_pk, project=project)

    if cat.category_type == BudgetCategory.CategoryType.LABOUR:
        messages.error(request, 'Kategorii LABOUR nie można usunąć — jest zarządzana automatycznie.')
    else:
        cat.delete()

    return redirect('project_budget', pk=pk)

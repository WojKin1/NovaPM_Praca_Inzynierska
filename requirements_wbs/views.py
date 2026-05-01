import re

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from projects.models import Project
from resources.models import ProjectMember
from .forms import RequirementForm, WBSElementForm
from .models import Requirement, WBSElement
from .services import generate_next_code, get_tree, recalculate_codes, would_create_cycle


def _get_member(user, project):
    return ProjectMember.objects.filter(
        project=project, user=user, is_active=True
    ).first()


def _can_access(user, project):
    if project.project_manager == user or user.is_staff:
        return True
    return _get_member(user, project) is not None


def _can_edit(user, project):
    if project.project_manager == user or user.is_staff:
        return True
    m = _get_member(user, project)
    return m is not None and m.role_in_project == ProjectMember.RoleInProject.ANALYST


def _require_access(user, project):
    if not _can_access(user, project):
        raise PermissionDenied


def _require_edit(user, project):
    if not _can_edit(user, project):
        raise PermissionDenied


def _next_code(project):
    codes = list(
        Requirement.objects.filter(project=project)
        .values_list('code', flat=True)
    )
    max_num = 0
    for code in codes:
        m = re.search(r'(\d+)$', code)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f'REQ-{max_num + 1:03d}'


def _req_stats(project):
    qs = project.requirements.all()
    return {
        'total':       qs.count(),
        'draft':       qs.filter(status=Requirement.Status.DRAFT).count(),
        'approved':    qs.filter(status=Requirement.Status.APPROVED).count(),
        'implemented': qs.filter(status=Requirement.Status.IMPLEMENTED).count(),
        'rejected':    qs.filter(status=Requirement.Status.REJECTED).count(),
        'wbs_total':   project.wbs_elements.count(),
    }


@login_required
def my_requirements_projects(request):
    member_project_ids = ProjectMember.objects.filter(
        user=request.user, is_active=True
    ).values_list('project_id', flat=True)

    projects = Project.objects.filter(pk__in=member_project_ids).order_by('name')

    project_cards = []
    for p in projects:
        project_cards.append({
            'project': p,
            'stats':   _req_stats(p),
        })

    return render(request, 'requirements_wbs/my_projects.html', {
        'project_cards': project_cards,
    })


@login_required
def project_requirements(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_access(request.user, project)

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    can_edit = _can_edit(request.user, project)

    qs = project.requirements.order_by('code')

    type_filter   = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    if type_filter:
        qs = qs.filter(req_type=type_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)

    stats = _req_stats(project)

    return render(request, 'requirements_wbs/project_requirements.html', {
        'project':        project,
        'requirements':   qs,
        'stats':          stats,
        'type_filter':    type_filter,
        'status_filter':  status_filter,
        'is_pm_or_staff': is_pm_or_staff,
        'can_edit':       can_edit,
    })


@login_required
def requirement_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_edit(request.user, project)

    if request.method == 'POST':
        form = RequirementForm(request.POST, project=project)
        if form.is_valid():
            req = form.save(commit=False)
            req.project = project
            req.created_by = request.user
            req.save()
            return redirect('project_requirements', project_pk=project_pk)
    else:
        form = RequirementForm(
            project=project,
            initial={'code': _next_code(project)},
        )

    return render(request, 'requirements_wbs/requirement_form.html', {
        'form':        form,
        'project':     project,
        'requirement': None,
    })


@login_required
def requirement_edit(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_edit(request.user, project)
    req = get_object_or_404(Requirement, pk=pk, project=project)

    if request.method == 'POST':
        form = RequirementForm(request.POST, instance=req, project=project)
        if form.is_valid():
            form.save()
            return redirect('project_requirements', project_pk=project_pk)
    else:
        form = RequirementForm(instance=req, project=project)

    return render(request, 'requirements_wbs/requirement_form.html', {
        'form':        form,
        'project':     project,
        'requirement': req,
    })


@login_required
@require_POST
def requirement_delete(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    req = get_object_or_404(Requirement, pk=pk, project=project)

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    is_author = (req.created_by == request.user)
    if not is_pm_or_staff and not is_author:
        raise PermissionDenied

    req.delete()
    return redirect('project_requirements', project_pk=project_pk)


# ─── WBS views ────────────────────────────────────────────────────────────────

@login_required
def project_wbs(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_access(request.user, project)

    is_pm_or_staff = (project.project_manager == request.user or request.user.is_staff)
    can_edit = _can_edit(request.user, project)

    tree = get_tree(project)

    all_qs = WBSElement.objects.filter(project=project)
    total = all_qs.count()
    roots = all_qs.filter(parent=None).count()
    codes = list(all_qs.values_list('code', flat=True))
    max_level = max((c.count('.') + 1 for c in codes if c), default=0)

    return render(request, 'requirements_wbs/project_wbs.html', {
        'project':        project,
        'tree':           tree,
        'can_edit':       can_edit,
        'is_pm_or_staff': is_pm_or_staff,
        'stats': {
            'total':     total,
            'roots':     roots,
            'max_level': max_level,
        },
    })


@login_required
def wbs_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_edit(request.user, project)

    parent = None
    parent_id = request.GET.get('parent') or request.POST.get('parent_id')
    if parent_id:
        parent = get_object_or_404(WBSElement, pk=parent_id, project=project)

    if request.method == 'POST':
        form = WBSElementForm(request.POST, project=project)
        if form.is_valid():
            el = form.save(commit=False)
            el.project = project
            chosen_parent = form.cleaned_data.get('parent')
            el.code = generate_next_code(project, chosen_parent)
            siblings = WBSElement.objects.filter(project=project, parent=chosen_parent)
            el.order = siblings.count()
            el.save()
            return redirect('project_wbs', project_pk=project_pk)
    else:
        form = WBSElementForm(project=project, initial={'parent': parent})

    return render(request, 'requirements_wbs/wbs_form.html', {
        'form':           form,
        'project':        project,
        'element':        None,
        'preset_parent':  parent,
        'is_pm_or_staff': (project.project_manager == request.user or request.user.is_staff),
    })


@login_required
def wbs_edit(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_edit(request.user, project)
    el = get_object_or_404(WBSElement, pk=pk, project=project)

    if request.method == 'POST':
        form = WBSElementForm(request.POST, project=project, instance=el)
        if form.is_valid():
            new_parent = form.cleaned_data.get('parent')
            if new_parent and would_create_cycle(el, new_parent):
                form.add_error('parent', 'Wybrany rodzic tworzyłby cykl w strukturze WBS.')
            else:
                parent_changed = (el.parent_id != (new_parent.pk if new_parent else None))
                form.save()
                if parent_changed:
                    recalculate_codes(project)
                return redirect('project_wbs', project_pk=project_pk)
    else:
        form = WBSElementForm(project=project, instance=el)

    return render(request, 'requirements_wbs/wbs_form.html', {
        'form':           form,
        'project':        project,
        'element':        el,
        'preset_parent':  None,
        'is_pm_or_staff': (project.project_manager == request.user or request.user.is_staff),
    })


@login_required
@require_POST
def wbs_delete(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_edit(request.user, project)
    el = get_object_or_404(WBSElement, pk=pk, project=project)
    el.delete()
    recalculate_codes(project)
    return redirect('project_wbs', project_pk=project_pk)


@login_required
@require_POST
def wbs_move(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    _require_edit(request.user, project)
    el = get_object_or_404(WBSElement, pk=pk, project=project)

    direction = request.POST.get('direction')
    siblings = list(WBSElement.objects.filter(project=project, parent=el.parent).order_by('order'))
    idx = next((i for i, s in enumerate(siblings) if s.id == el.id), None)

    if idx is None:
        return redirect('project_wbs', project_pk=project_pk)

    if direction == 'up' and idx > 0:
        swap = siblings[idx - 1]
    elif direction == 'down' and idx < len(siblings) - 1:
        swap = siblings[idx + 1]
    else:
        return redirect('project_wbs', project_pk=project_pk)

    el.order, swap.order = swap.order, el.order
    el.save(update_fields=['order'])
    swap.save(update_fields=['order'])
    recalculate_codes(project)
    return redirect('project_wbs', project_pk=project_pk)

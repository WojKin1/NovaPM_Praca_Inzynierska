import calendar
import csv
import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect

from budget.models import BudgetCategory, Timesheet
from budget.services import get_labour_breakdown
from changes.models import ChangeRequest
from projects.models import Project
from requirements_wbs.models import Requirement, WBSElement
from resources.models import ProjectMember
from risks.models import Risk
from tasks.models import Task, TaskReview

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ── Font registration — DejaVu (Linux/Render), Arial (Windows), fallback Helvetica
import os as _os

_DEJAVU_PATHS = [
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
     '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('/usr/share/fonts/dejavu/DejaVuSans.ttf',
     '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf',
     '/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans-Bold.ttf'),
]
_ARIAL_PATHS = [
    ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
]

def _try_register(regular, bold):
    pdfmetrics.registerFont(TTFont('PDF-Regular', regular))
    pdfmetrics.registerFont(TTFont('PDF-Bold', bold))

FONT = FONT_BOLD = None
for _r, _b in _DEJAVU_PATHS + _ARIAL_PATHS:
    if _os.path.exists(_r) and _os.path.exists(_b):
        try:
            _try_register(_r, _b)
            FONT      = 'PDF-Regular'
            FONT_BOLD = 'PDF-Bold'
            break
        except Exception:
            pass

if not FONT:
    FONT      = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

# ── Colors ────────────────────────────────────────────────────────────────────
C_HEADER = colors.HexColor('#374151')
C_TH_BG  = colors.HexColor('#F3F4F6')
C_ALT_BG = colors.HexColor('#F9FAFB')
C_BORDER = colors.HexColor('#E5E7EB')
C_GRAY   = colors.HexColor('#6B7280')
C_WHITE  = colors.white
C_BLACK  = colors.black
C_RED    = colors.HexColor('#DC2626')
C_ORANGE = colors.HexColor('#D97706')
C_GREEN  = colors.HexColor('#059669')

# ── Page geometry ─────────────────────────────────────────────────────────────
PAGE_W = A4[0] - 4 * cm


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _styles():
    return {
        'h2':     ParagraphStyle('h2',     fontName=FONT_BOLD, fontSize=11, textColor=C_WHITE,
                                 backColor=C_HEADER, spaceBefore=10, spaceAfter=4,
                                 leftIndent=4, leading=16),
        'normal': ParagraphStyle('normal', fontName=FONT,      fontSize=8,  spaceAfter=2),
        'bold':   ParagraphStyle('bold',   fontName=FONT_BOLD, fontSize=8),
        'summ':   ParagraphStyle('summ',   fontName=FONT_BOLD, fontSize=8,  spaceBefore=4,
                                 spaceAfter=4),
        'indent1': ParagraphStyle('indent1', fontName=FONT, fontSize=8, leftIndent=14),
        'indent2': ParagraphStyle('indent2', fontName=FONT, fontSize=8, leftIndent=28),
        'indent3': ParagraphStyle('indent3', fontName=FONT, fontSize=8, leftIndent=42),
    }


def _cell(text, bold=False, max_len=None):
    """Wrap text in Paragraph for word-wrap inside Table cells."""
    text = str(text) if text is not None else '—'
    if not text:
        text = '—'
    if max_len and len(text) > max_len:
        text = text[:max_len] + '...'
    style = ParagraphStyle(
        'cell',
        fontName=FONT_BOLD if bold else FONT,
        fontSize=8,
        leading=10,
    )
    return Paragraph(text, style)


def _table_style(header_rows=1):
    cmds = [
        ('FONTNAME',      (0, 0),              (-1, -1),             FONT),
        ('FONTSIZE',      (0, 0),              (-1, -1),             8),
        ('GRID',          (0, 0),              (-1, -1),             0.5, C_BORDER),
        ('TOPPADDING',    (0, 0),              (-1, -1),             3),
        ('BOTTOMPADDING', (0, 0),              (-1, -1),             3),
        ('LEFTPADDING',   (0, 0),              (-1, -1),             5),
        ('RIGHTPADDING',  (0, 0),              (-1, -1),             5),
        ('VALIGN',        (0, 0),              (-1, -1),             'TOP'),
        ('ROWBACKGROUNDS', (0, header_rows),   (-1, -1),             [C_WHITE, C_ALT_BG]),
    ]
    if header_rows:
        cmds += [
            ('BACKGROUND', (0, 0),             (-1, header_rows - 1), C_TH_BG),
            ('FONTNAME',   (0, 0),             (-1, header_rows - 1), FONT_BOLD),
            ('LINEBELOW',  (0, header_rows-1), (-1, header_rows - 1), 1, C_HEADER),
        ]
    return TableStyle(cmds)


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(C_GRAY)
    w, _ = A4
    canvas.drawString(
        2 * cm, 1.2 * cm,
        f'Wygenerowano: {date.today().strftime("%d.%m.%Y")} | NovaPM System Zarządzania Projektami',
    )
    canvas.drawRightString(w - 2 * cm, 1.2 * cm, f'Strona {canvas._pageNumber}')
    canvas.restoreState()


def _new_doc(buffer):
    return SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )


def _pdf_response(buffer, filename):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(buffer.getvalue())
    return response


def _report_header(story, title, subtitle=''):
    """Two-column NovaPM / report-type header with separator line."""
    hdr = Table(
        [[
            Paragraph('<b>NovaPM</b>',
                      ParagraphStyle('logo', fontName=FONT_BOLD, fontSize=20, textColor=C_HEADER)),
            Paragraph(title,
                      ParagraphStyle('rtype', fontName=FONT_BOLD, fontSize=11, alignment=TA_RIGHT)),
        ]],
        colWidths=[PAGE_W * 0.5, PAGE_W * 0.5],
    )
    hdr.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'BOTTOM'),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  10),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.5, C_HEADER),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6))
    if subtitle:
        story.append(Paragraph(
            subtitle,
            ParagraphStyle('sub', fontName=FONT, fontSize=8, textColor=C_GRAY,
                           alignment=TA_RIGHT, spaceBefore=0, spaceAfter=8),
        ))


def _month_range(month_param):
    today = date.today()
    if month_param:
        try:
            year, mon = map(int, month_param.split('-'))
        except (ValueError, AttributeError):
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month
    _, last_day = calendar.monthrange(year, mon)
    return date(year, mon, 1), date(year, mon, last_day), f'{mon:02d}.{year}', year, mon


# ════════════════════════════════════════════════════════════════════════════
# PART 1 — PM: Project status report (PDF)
# ════════════════════════════════════════════════════════════════════════════

@login_required
def pm_project_report(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not (request.user.is_staff or request.user.role == 'PM'):
        return redirect('project_detail', pk=pk)

    today = date.today()
    st = _styles()

    tasks = list(project.tasks.select_related('assigned_to').all())
    task_total = len(tasks)
    task_done  = sum(1 for t in tasks if t.status == 'DONE')
    task_pct   = round(task_done / task_total * 100) if task_total else 0
    task_counts = {s: sum(1 for t in tasks if t.status == s)
                   for s in ('TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE', 'BLOCKED')}

    cats          = list(project.budget_categories.all())
    total_planned = sum(c.planned_amount for c in cats) or Decimal('0')
    total_spent   = sum(c.spent_amount   for c in cats) or Decimal('0')
    budget_pct    = round(total_spent / total_planned * 100) if total_planned else 0

    days_left      = (project.end_date - today).days
    active_risks   = list(Risk.objects.filter(project=project).exclude(status='CLOSED')
                          .order_by('-probability', '-impact'))
    change_requests = list(ChangeRequest.objects.filter(project=project).order_by('-created_at'))
    labour_rows    = get_labour_breakdown(project)

    buf = io.BytesIO()
    doc = _new_doc(buf)
    story = []

    _report_header(story, 'RAPORT STATUSOWY PROJEKTU',
                   f'Data generowania: {today.strftime("%d.%m.%Y")}')

    # 1. Project info
    story.append(Paragraph('1. Informacje o projekcie', st['h2']))
    pm_name = project.project_manager.get_full_name() or project.project_manager.username
    info = [
        ['Nazwa projektu:', _cell(project.name),       'Status:',    project.get_status_display()],
        ['Klient:',         _cell(project.client_name), 'Priorytet:', project.get_priority_display()],
        ['Rozpoczęcie:',    project.start_date.strftime('%d.%m.%Y'),
         'Zakończenie:',    project.end_date.strftime('%d.%m.%Y')],
        ['Kierownik:',      _cell(pm_name), '', ''],
    ]
    info_tbl = Table(info, colWidths=[PAGE_W*0.2, PAGE_W*0.3, PAGE_W*0.2, PAGE_W*0.3])
    info_tbl.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, -1), FONT),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('FONTNAME',      (0, 0), (0, -1),  FONT_BOLD),
        ('FONTNAME',      (2, 0), (2, -1),  FONT_BOLD),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [C_WHITE, C_ALT_BG]),
    ]))
    story.append(info_tbl)

    # 2. KPIs
    story.append(Paragraph('2. Wskaźniki projektu (KPI)', st['h2']))
    days_str = (f'{days_left} dni do terminu' if days_left >= 0
                else f'{-days_left} dni po terminie')
    kpi_tbl = Table(
        [['Postęp zadań', 'Wykorzystanie budżetu', 'Czas', 'Aktywne ryzyka'],
         [f'{task_done}/{task_total}\n({task_pct}%)',
          f'{total_spent:.0f}/{total_planned:.0f} zł\n({budget_pct}%)',
          days_str,
          str(len(active_risks))]],
        colWidths=[PAGE_W / 4] * 4,
    )
    kpi_tbl.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, 0),  FONT_BOLD),
        ('FONTNAME',      (0, 1), (-1, 1),  FONT_BOLD),
        ('FONTSIZE',      (0, 0), (-1, 0),  8),
        ('FONTSIZE',      (0, 1), (-1, 1),  12),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND',    (0, 0), (-1, 0),  C_TH_BG),
        ('GRID',          (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (3, 1), (3, 1), C_RED if active_risks else C_GREEN),
        ('TEXTCOLOR', (2, 1), (2, 1), C_RED if days_left < 0 else C_BLACK),
    ]))
    story.append(kpi_tbl)

    # 3. Task progress
    story.append(Paragraph('3. Postęp zadań', st['h2']))
    status_labels = [
        ('TODO', 'Do zrobienia'), ('IN_PROGRESS', 'W trakcie'),
        ('IN_REVIEW', 'W przeglądzie'), ('DONE', 'Ukończone'), ('BLOCKED', 'Zablokowane'),
    ]
    task_rows = [['Status', 'Liczba', '%']]
    for key, label in status_labels:
        cnt = task_counts[key]
        pct = round(cnt / task_total * 100) if task_total else 0
        task_rows.append([label, str(cnt), f'{pct}%'])
    task_rows.append(['RAZEM', str(task_total), '100%'])
    task_tbl = Table(task_rows, colWidths=[PAGE_W*0.5, PAGE_W*0.25, PAGE_W*0.25])
    tts = _table_style()
    tts.add('FONTNAME',   (0, -1), (-1, -1), FONT_BOLD)
    tts.add('BACKGROUND', (0, -1), (-1, -1), C_TH_BG)
    task_tbl.setStyle(tts)
    story.append(task_tbl)

    # 4. Budget
    story.append(Paragraph('4. Budżet projektu', st['h2']))
    budget_rows = [['Kategoria', 'Typ', 'Planowano (zł)', 'Wydano (zł)', 'Pozostało (zł)', '%']]
    for cat in cats:
        remaining = cat.planned_amount - cat.spent_amount
        pct = round(cat.spent_amount / cat.planned_amount * 100) if cat.planned_amount else 0
        budget_rows.append([
            _cell(cat.name), cat.get_category_type_display(),
            f'{cat.planned_amount:.2f}', f'{cat.spent_amount:.2f}',
            f'{remaining:.2f}', f'{pct}%',
        ])
    budget_rows.append([
        'RAZEM', '',
        f'{total_planned:.2f}', f'{total_spent:.2f}',
        f'{total_planned - total_spent:.2f}', f'{budget_pct}%',
    ])
    cw = PAGE_W
    budget_tbl = Table(budget_rows,
                       colWidths=[cw*0.25, cw*0.15, cw*0.15, cw*0.15, cw*0.15, cw*0.15])
    bts = _table_style()
    bts.add('FONTNAME',   (0, -1), (-1, -1), FONT_BOLD)
    bts.add('BACKGROUND', (0, -1), (-1, -1), C_TH_BG)
    budget_tbl.setStyle(bts)
    story.append(budget_tbl)

    # 5. Labour costs
    story.append(Paragraph('5. Koszty zespołu', st['h2']))
    if labour_rows:
        labour_data = [['Pracownik', 'Rola', 'Zatw. godz.', 'Stawka (zł/h)', 'Koszt (zł)']]
        total_h = Decimal('0')
        total_c = Decimal('0')
        for row in labour_rows:
            labour_data.append([
                _cell(row['full_name']), _cell(row['role_display']),
                f"{row['hours']:.1f}h", f"{row['rate']:.2f}", f"{row['cost']:.2f}",
            ])
            total_h += row['hours']
            total_c += row['cost']
        labour_data.append(['RAZEM', '', f'{total_h:.1f}h', '', f'{total_c:.2f}'])
        lw = PAGE_W
        labour_tbl = Table(labour_data, colWidths=[lw*0.3, lw*0.2, lw*0.15, lw*0.15, lw*0.2])
        lts = _table_style()
        lts.add('FONTNAME',   (0, -1), (-1, -1), FONT_BOLD)
        lts.add('BACKGROUND', (0, -1), (-1, -1), C_TH_BG)
        labour_tbl.setStyle(lts)
        story.append(labour_tbl)
    else:
        story.append(Paragraph('Brak zatwierdzonych wpisów czasu pracy.', st['normal']))

    # 6. Active risks
    story.append(Paragraph('6. Aktywne ryzyka', st['h2']))
    if active_risks:
        risk_data = [['Nazwa', 'Prawdopodob.', 'Wpływ', 'Poziom', 'Status']]
        for risk in active_risks:
            level = risk.risk_level
            risk_data.append([
                _cell(risk.title), risk.get_probability_display(),
                risk.get_impact_display(), str(level), risk.get_status_display(),
            ])
        rw = PAGE_W
        risk_tbl = Table(risk_data, colWidths=[rw*0.35, rw*0.17, rw*0.14, rw*0.1, rw*0.24])
        rts = _table_style()
        for i, row_d in enumerate(risk_data[1:], start=1):
            lvl = int(row_d[3])
            if lvl > 12:
                rts.add('TEXTCOLOR', (3, i), (3, i), C_RED)
            elif lvl > 6:
                rts.add('TEXTCOLOR', (3, i), (3, i), C_ORANGE)
        risk_tbl.setStyle(rts)
        story.append(risk_tbl)
    else:
        story.append(Paragraph('Brak aktywnych ryzyk.', st['normal']))

    # 7. Change requests
    story.append(Paragraph('7. Wnioski o zmianę', st['h2']))
    if change_requests:
        cr_data = [['Tytuł', 'Wnioskodawca', 'Status', 'Data złożenia']]
        for cr in change_requests:
            requester = cr.requested_by.get_full_name() or cr.requested_by.username
            cr_data.append([
                _cell(cr.title), _cell(requester),
                cr.get_status_display(), cr.created_at.strftime('%d.%m.%Y'),
            ])
        cr_tbl = Table(cr_data, colWidths=[PAGE_W*0.4, PAGE_W*0.25, PAGE_W*0.15, PAGE_W*0.2])
        cr_tbl.setStyle(_table_style())
        story.append(cr_tbl)
    else:
        story.append(Paragraph('Brak wniosków o zmianę.', st['normal']))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return _pdf_response(buf, f'raport_{project.pk}_{today.strftime("%Y%m%d")}.pdf')


# ════════════════════════════════════════════════════════════════════════════
# PART 2 — Analyst: Requirements report (PDF + CSV)
# ════════════════════════════════════════════════════════════════════════════

@login_required
def analyst_requirements_report(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    is_pm = request.user.is_staff or request.user.role == 'PM'
    is_analyst = (
        request.user.role == 'ANALYST'
        and ProjectMember.objects.filter(
            project=project, user=request.user, is_active=True
        ).exists()
    )
    if not (is_pm or is_analyst):
        return redirect('project_detail', pk=project_pk)

    today = date.today()
    fmt = request.GET.get('format', 'pdf')

    requirements = Requirement.objects.filter(project=project).order_by('code')
    wbs_elements = WBSElement.objects.filter(project=project).order_by('code', 'order')
    req_stats = {
        'total':       requirements.count(),
        'draft':       requirements.filter(status='DRAFT').count(),
        'approved':    requirements.filter(status='APPROVED').count(),
        'implemented': requirements.filter(status='IMPLEMENTED').count(),
        'rejected':    requirements.filter(status='REJECTED').count(),
    }

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = (
            f'attachment; filename="wymagania_{project.pk}_{today.strftime("%Y%m%d")}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(['Kod', 'Tytuł', 'Typ', 'Priorytet', 'Status', 'Data utworzenia', 'Autor'])
        for req in requirements:
            writer.writerow([
                req.code, req.title,
                req.get_req_type_display(), req.get_priority_display(), req.get_status_display(),
                req.created_at.strftime('%d.%m.%Y'),
                req.created_by.get_full_name() or req.created_by.username,
            ])
        return response

    st = _styles()
    buf = io.BytesIO()
    doc = _new_doc(buf)
    story = []

    _report_header(story, 'RAPORT WYMAGAŃ',
                   f'Projekt: {project.name} | Data: {today.strftime("%d.%m.%Y")}')

    # 1. Summary
    story.append(Paragraph('1. Podsumowanie', st['h2']))
    summ_tbl = Table(
        [['Łącznie', 'Szkic', 'Zatwierdzone', 'Zrealizowane', 'Odrzucone'],
         [str(req_stats['total']), str(req_stats['draft']), str(req_stats['approved']),
          str(req_stats['implemented']), str(req_stats['rejected'])]],
        colWidths=[PAGE_W / 5] * 5,
    )
    summ_tbl.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, 0),  FONT_BOLD),
        ('FONTNAME',      (0, 1), (-1, 1),  FONT_BOLD),
        ('FONTSIZE',      (0, 1), (-1, 1),  14),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND',    (0, 0), (-1, 0),  C_TH_BG),
        ('GRID',          (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(summ_tbl)

    # 2. Requirements table
    story.append(Paragraph('2. Lista wymagań', st['h2']))
    if requirements.exists():
        req_data = [['Kod', 'Tytuł', 'Typ', 'Priorytet', 'Status']]
        for req in requirements:
            req_data.append([
                req.code, _cell(req.title),
                req.get_req_type_display(), req.get_priority_display(), req.get_status_display(),
            ])
        rw = PAGE_W
        req_tbl = Table(req_data, colWidths=[rw*0.1, rw*0.4, rw*0.18, rw*0.15, rw*0.17])
        req_tbl.setStyle(_table_style())
        story.append(req_tbl)
    else:
        story.append(Paragraph('Brak wymagań.', st['normal']))

    # 3. WBS tree
    story.append(Paragraph('3. Struktura WBS', st['h2']))
    if wbs_elements.exists():
        indent_map = {1: st['bold'], 2: st['indent1'], 3: st['indent2']}
        for el in wbs_elements:
            level = min(el.level, 3)
            el_st = indent_map.get(level, st['indent3'])
            prefix = f'{el.code} ' if el.code else ''
            story.append(Paragraph(f'{prefix}{el.name}', el_st))
    else:
        story.append(Paragraph('Brak elementów WBS.', st['normal']))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return _pdf_response(buf, f'wymagania_{project.pk}_{today.strftime("%Y%m%d")}.pdf')


# ════════════════════════════════════════════════════════════════════════════
# PART 3 — Developer: Personal report
# ════════════════════════════════════════════════════════════════════════════

@login_required
def developer_report(request):
    month_start, month_end, month_label, year, mon = _month_range(
        request.GET.get('month', '')
    )
    user = request.user
    st = _styles()

    tasks = (
        Task.objects.filter(assigned_to=user, due_date__gte=month_start, due_date__lte=month_end)
        .select_related('project').order_by('project__name', 'due_date')
    )
    timesheets = (
        Timesheet.objects.filter(user=user, date__gte=month_start, date__lte=month_end)
        .select_related('project', 'task').order_by('date')
    )
    reviews = list(
        TaskReview.objects.filter(task__assigned_to=user)
        .select_related('task', 'task__project', 'reviewer')
        .order_by('-created_at')[:50]
    )

    ts_list       = list(timesheets)
    ts_total_h    = sum(t.hours for t in ts_list)
    ts_approved_h = sum(t.hours for t in ts_list if t.is_approved)
    ts_pending_h  = ts_total_h - ts_approved_h

    buf = io.BytesIO()
    doc = _new_doc(buf)
    story = []

    user_name = user.get_full_name() or user.username
    _report_header(story, 'RAPORT OSOBISTY',
                   f'{user_name} | {user.get_role_display()} | Okres: {month_label}')

    # 1. Tasks
    story.append(Paragraph('1. Zadania', st['h2']))
    task_list = list(tasks)
    if task_list:
        status_map = {
            'TODO': 'Do zrobienia', 'IN_PROGRESS': 'W trakcie',
            'IN_REVIEW': 'W przeglądzie', 'DONE': 'Ukończone', 'BLOCKED': 'Zablokowane',
        }
        task_data = [['Projekt', 'Zadanie', 'Status', 'Termin', 'Estym.', 'Rzecz.']]
        done_cnt = in_prog_cnt = 0
        for t in task_list:
            task_data.append([
                _cell(t.project.name), _cell(t.title),
                status_map.get(t.status, t.status),
                t.due_date.strftime('%d.%m.%Y'),
                f'{t.estimated_hours}h', f'{t.actual_hours}h',
            ])
            if t.status == 'DONE':
                done_cnt += 1
            elif t.status == 'IN_PROGRESS':
                in_prog_cnt += 1
        tw = PAGE_W
        task_tbl = Table(task_data,
                         colWidths=[tw*0.2, tw*0.3, tw*0.15, tw*0.12, tw*0.1, tw*0.13])
        task_tbl.setStyle(_table_style())
        story.append(task_tbl)
        story.append(Paragraph(
            f'Łącznie: {len(task_list)} | Ukończone: {done_cnt} | W trakcie: {in_prog_cnt}',
            st['summ'],
        ))
    else:
        story.append(Paragraph(f'Brak zadań z terminem w okresie {month_label}.', st['normal']))

    # 2. Timesheet
    story.append(Paragraph('2. Ewidencja czasu pracy', st['h2']))
    if ts_list:
        ts_data = [['Data', 'Projekt', 'Zadanie', 'Godz.', 'Status']]
        for ts_entry in ts_list:
            if ts_entry.is_approved:
                status_str = 'Zatwierdzone'
            elif ts_entry.rejected_by_id:
                status_str = 'Odrzucone'
            else:
                status_str = 'Oczekuje'
            ts_data.append([
                ts_entry.date.strftime('%d.%m.%Y'),
                _cell(ts_entry.project.name),
                _cell(ts_entry.task.title if ts_entry.task else '—'),
                f'{ts_entry.hours}h',
                status_str,
            ])
        ttsw = PAGE_W
        ts_tbl = Table(ts_data, colWidths=[ttsw*0.13, ttsw*0.27, ttsw*0.3, ttsw*0.1, ttsw*0.2])
        ts_tbl.setStyle(_table_style())
        story.append(ts_tbl)
        story.append(Paragraph(
            f'Łącznie: {ts_total_h:.1f}h | Zatwierdzone: {ts_approved_h:.1f}h | Oczekuje: {ts_pending_h:.1f}h',
            st['summ'],
        ))
    else:
        story.append(Paragraph(f'Brak wpisów czasu pracy w okresie {month_label}.', st['normal']))

    # 3. Review history (developer only)
    if user.role == 'DEVELOPER' and reviews:
        story.append(Paragraph('3. Historia przeglądów kodu', st['h2']))
        rev_data = [['Zadanie', 'Projekt', 'Data', 'Wynik', 'Komentarz testera']]
        approved_cnt = rejected_cnt = 0
        for rv in reviews:
            result_str = 'Zatwierdz.' if rv.result == 'APPROVED' else 'Odrzucono'
            rev_data.append([
                _cell(rv.task.title), _cell(rv.task.project.name),
                rv.created_at.strftime('%d.%m.%Y'),
                result_str,
                _cell(rv.comment or '—'),
            ])
            if rv.result == 'APPROVED':
                approved_cnt += 1
            else:
                rejected_cnt += 1
        rw = PAGE_W
        rev_tbl = Table(rev_data, colWidths=[rw*0.28, rw*0.22, rw*0.1, rw*0.1, rw*0.3])
        rev_tbl.setStyle(_table_style())
        story.append(rev_tbl)
        story.append(Paragraph(
            f'Zatwierdzono: {approved_cnt} | Odrzucono: {rejected_cnt}',
            st['summ'],
        ))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return _pdf_response(buf, f'raport_osobisty_{user.username}_{year}{mon:02d}.pdf')


# ════════════════════════════════════════════════════════════════════════════
# PART 4 — Tester: QA report
# ════════════════════════════════════════════════════════════════════════════

@login_required
def tester_report(request):
    month_start, month_end, month_label, year, mon = _month_range(
        request.GET.get('month', '')
    )
    user = request.user
    st = _styles()

    reviews = list(
        TaskReview.objects.filter(
            reviewer=user,
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
        )
        .select_related('task', 'task__project', 'task__assigned_to')
        .order_by('-created_at')
    )
    timesheets = list(
        Timesheet.objects.filter(user=user, date__gte=month_start, date__lte=month_end)
        .select_related('project', 'task').order_by('date')
    )

    total_reviews = len(reviews)
    approved_cnt  = sum(1 for r in reviews if r.result == 'APPROVED')
    rejected_cnt  = sum(1 for r in reviews if r.result == 'REJECTED')
    approval_rate = round(approved_cnt / total_reviews * 100) if total_reviews else 0
    ts_total_h    = sum(t.hours for t in timesheets)

    buf = io.BytesIO()
    doc = _new_doc(buf)
    story = []

    user_name = user.get_full_name() or user.username
    _report_header(story, 'RAPORT QA',
                   f'{user_name} | {user.get_role_display()} | Okres: {month_label}')

    # 1. Summary stats
    story.append(Paragraph('1. Podsumowanie testów', st['h2']))
    summ_tbl = Table(
        [['Przeprowadzono', 'Zatwierdzono', 'Odrzucono', 'Wskaźnik zatwierdzenia'],
         [str(total_reviews), str(approved_cnt), str(rejected_cnt), f'{approval_rate}%']],
        colWidths=[PAGE_W / 4] * 4,
    )
    summ_tbl.setStyle(TableStyle([
        ('FONTNAME',      (0, 0), (-1, 0),  FONT_BOLD),
        ('FONTNAME',      (0, 1), (-1, 1),  FONT_BOLD),
        ('FONTSIZE',      (0, 1), (-1, 1),  16),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND',    (0, 0), (-1, 0),  C_TH_BG),
        ('GRID',          (0, 0), (-1, -1), 0.5, C_BORDER),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (1, 1), (1, 1), C_GREEN),
        ('TEXTCOLOR', (2, 1), (2, 1), C_RED if rejected_cnt else C_BLACK),
        ('TEXTCOLOR', (3, 1), (3, 1),
         C_GREEN if approval_rate >= 70 else C_ORANGE if approval_rate >= 40 else C_RED),
    ]))
    story.append(summ_tbl)

    # 2. Review details
    story.append(Paragraph('2. Szczegóły testów', st['h2']))
    if reviews:
        rev_data = [['Data', 'Projekt', 'Zadanie', 'Developer', 'Wynik', 'Komentarz']]
        for rv in reviews:
            dev = rv.task.assigned_to.username if rv.task.assigned_to else '—'
            result_str = 'Zatwierdz.' if rv.result == 'APPROVED' else 'Odrzucono'
            rev_data.append([
                rv.created_at.strftime('%d.%m.%Y'),
                _cell(rv.task.project.name),
                _cell(rv.task.title),
                dev,
                result_str,
                _cell(rv.comment or '—'),
            ])
        rw = PAGE_W
        rev_tbl = Table(rev_data,
                        colWidths=[rw*0.11, rw*0.22, rw*0.20, rw*0.1, rw*0.1, rw*0.27])
        rts = _table_style()
        for i, row_d in enumerate(rev_data[1:], start=1):
            if row_d[4] == 'Zatwierdz.':
                rts.add('TEXTCOLOR', (4, i), (4, i), C_GREEN)
            else:
                rts.add('TEXTCOLOR', (4, i), (4, i), C_RED)
        rev_tbl.setStyle(rts)
        story.append(rev_tbl)
    else:
        story.append(Paragraph(f'Brak przeglądów w okresie {month_label}.', st['normal']))

    # 3. Timesheet
    story.append(Paragraph('3. Ewidencja czasu pracy', st['h2']))
    if timesheets:
        ts_data = [['Data', 'Projekt', 'Zadanie', 'Godz.', 'Status']]
        for ts_entry in timesheets:
            if ts_entry.is_approved:
                status_str = 'Zatwierdzone'
            elif ts_entry.rejected_by_id:
                status_str = 'Odrzucone'
            else:
                status_str = 'Oczekuje'
            ts_data.append([
                ts_entry.date.strftime('%d.%m.%Y'),
                _cell(ts_entry.project.name),
                _cell(ts_entry.task.title if ts_entry.task else '—'),
                f'{ts_entry.hours}h',
                status_str,
            ])
        ttsw = PAGE_W
        ts_tbl = Table(ts_data, colWidths=[ttsw*0.13, ttsw*0.3, ttsw*0.27, ttsw*0.1, ttsw*0.2])
        ts_tbl.setStyle(_table_style())
        story.append(ts_tbl)
        story.append(Paragraph(f'Łącznie godzin w tym okresie: {ts_total_h:.1f}h', st['summ']))
    else:
        story.append(Paragraph(f'Brak wpisów czasu pracy w okresie {month_label}.', st['normal']))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return _pdf_response(buf, f'raport_qa_{user.username}_{year}{mon:02d}.pdf')


# ════════════════════════════════════════════════════════════════════════════
# PART 5 — Reports index (role-based redirect)
# ════════════════════════════════════════════════════════════════════════════

@login_required
def reports_index(request):
    role = request.user.role
    if request.user.is_staff or role == 'PM':
        return redirect('project_list')
    if role == 'ANALYST':
        return redirect('my_requirements_projects')
    if role == 'TESTER':
        return redirect('tester_report')
    return redirect('developer_report')

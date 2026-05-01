from django.contrib import admin, messages
from django.shortcuts import render
from django.utils import timezone

from .models import BudgetCategory, Timesheet


def approve_timesheets(modeladmin, request, queryset):
    count = queryset.count()
    queryset.update(
        is_approved=True,
        approved_by=request.user,
        approved_at=timezone.now(),
        rejected_by=None,
        rejected_at=None,
        rejection_reason='',
    )
    modeladmin.message_user(request, f'Zatwierdzono {count} wpisów.')


approve_timesheets.short_description = 'Zatwierdź zaznaczone wpisy'


def reject_timesheets(modeladmin, request, queryset):
    if 'apply' in request.POST:
        reason = request.POST.get('rejection_reason', '').strip()
        if reason:
            count = queryset.count()
            queryset.update(
                is_approved=False,
                rejected_by=request.user,
                rejected_at=timezone.now(),
                rejection_reason=reason,
                approved_by=None,
                approved_at=None,
            )
            modeladmin.message_user(request, f'Odrzucono {count} wpisów.')
            return None

    return render(request, 'admin/budget/reject_timesheets.html', {
        'queryset': queryset,
        'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        'opts': modeladmin.model._meta,
    })


reject_timesheets.short_description = 'Odrzuć zaznaczone wpisy'


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'category_type', 'planned_amount', 'spent_amount')
    list_filter = ('category_type', 'project')

    def save_model(self, request, obj, form, change):
        if obj.category_type == BudgetCategory.CategoryType.LABOUR:
            existing = BudgetCategory.objects.filter(
                project=obj.project,
                category_type=BudgetCategory.CategoryType.LABOUR,
            ).exclude(pk=obj.pk)
            if existing.exists():
                self.message_user(
                    request,
                    'Kategoria LABOUR już istnieje dla tego projektu. Jest zarządzana automatycznie.',
                    level=messages.ERROR,
                )
                return
        super().save_model(request, obj, form, change)


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    add_fieldsets = (
        ('Wpis czasu pracy', {
            'fields': ('project', 'user', 'date', 'hours', 'task', 'description'),
        }),
        ('Zatwierdzenie (opcjonalne)', {
            'classes': ('collapse',),
            'fields': ('is_approved', 'approved_by', 'approved_at'),
        }),
    )

    fieldsets = (
        ('Wpis czasu pracy', {
            'fields': ('project', 'user', 'date', 'hours', 'task', 'description'),
        }),
        ('Status zatwierdzenia', {
            'fields': ('is_approved', 'approved_by', 'approved_at'),
        }),
        ('Odrzucenie', {
            'classes': ('collapse',),
            'fields': ('rejected_by', 'rejected_at', 'rejection_reason'),
            'description': 'Wypełnij tylko jeśli odrzucasz wpis pracownika.',
        }),
    )

    list_display = ('user', 'project', 'date', 'hours', 'task', 'approval_status_display')
    list_filter = ('is_approved', 'project', 'user')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'date'
    actions = [approve_timesheets, reject_timesheets]

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def approval_status_display(self, obj):
        if obj.is_approved:
            return '✓ Zatwierdzone'
        if obj.rejected_by:
            return '✗ Odrzucone'
        return '⏳ Oczekuje'

    approval_status_display.short_description = 'Status'

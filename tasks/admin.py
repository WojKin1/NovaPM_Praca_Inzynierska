from django.contrib import admin

from .models import Task, TaskReview


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assigned_to', 'status', 'priority', 'due_date')
    list_filter = ('status', 'priority')
    search_fields = ('title',)


@admin.register(TaskReview)
class TaskReviewAdmin(admin.ModelAdmin):
    list_display = ('task', 'reviewer', 'result', 'created_at')
    list_filter = ('result',)

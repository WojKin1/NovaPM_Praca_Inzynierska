from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'client_name', 'status', 'priority', 'project_manager', 'start_date', 'end_date')
    list_filter = ('status', 'priority')
    search_fields = ('name', 'client_name')

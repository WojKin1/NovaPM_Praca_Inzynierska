from django.contrib import admin

from .models import ProjectMember


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'role_in_project', 'availability_percent', 'is_active', 'joined_at')

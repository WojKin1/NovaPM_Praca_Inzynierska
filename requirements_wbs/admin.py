from django.contrib import admin

from .models import Requirement, WBSElement


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'req_type', 'priority', 'status', 'created_by')


@admin.register(WBSElement)
class WBSElementAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'parent', 'level', 'order')

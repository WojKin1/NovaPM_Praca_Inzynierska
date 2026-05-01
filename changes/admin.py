from django.contrib import admin

from .models import ChangeRequest


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'requested_by', 'status', 'impact_time', 'impact_cost')
    list_filter = ('status',)
    search_fields = ('title',)

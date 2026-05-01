from django.contrib import admin

from .models import Risk


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'probability', 'impact', 'status', 'owner')
    list_filter = ('status',)
    search_fields = ('title',)

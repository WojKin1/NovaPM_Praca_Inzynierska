from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'email'),
        }),
    )

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Dane osobowe', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('NovaPM', {'fields': ('role', 'is_active_employee', 'must_change_password')}),
        ('Uprawnienia', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Daty', {'fields': ('last_login', 'date_joined')}),
    )

    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active_employee', 'is_active']
    list_filter = ['role', 'is_active_employee', 'is_active', 'must_change_password']
    search_fields = ['username', 'email', 'first_name', 'last_name']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            obj.must_change_password = True
            obj.save(update_fields=['must_change_password'])

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

Group._meta.verbose_name = 'grupę'
Group._meta.verbose_name_plural = 'grupy'

admin.site.register(Group, GroupAdmin)

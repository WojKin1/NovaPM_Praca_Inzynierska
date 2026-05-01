"""
URL configuration for novapm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import novapm.admin_overrides  # noqa: F401 – patches Group verbose_name

from django.contrib import admin
from django.urls import include, path

from changes import views as changes_views

admin.site.site_header = "Panel administracyjny NovaPM"
admin.site.site_title = "NovaPM Admin"
admin.site.index_title = "Panel administracyjny"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('__reload__/', include('django_browser_reload.urls')),
    path('', include('accounts.urls')),
    path('projects/', include('projects.urls')),
    path('projects/<int:project_pk>/members/', include('resources.urls')),
    path('projects/<int:project_pk>/risks/', include('risks.urls')),
    path('projects/<int:project_pk>/changes/', include('changes.urls')),
    path('changes/new/', changes_views.cr_select_project, name='cr_select_project'),
    path('tasks/', include('tasks.urls')),
    path('timesheet/', include('budget.urls')),
    path('requirements/', include('requirements_wbs.urls')),
    path('reports/', include('reports.urls')),
]

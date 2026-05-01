from django.urls import path

from . import views
from budget import views as budget_views
from reports import views as report_views
from requirements_wbs import views as req_views
from tasks import views as tasks_views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('new/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/status/', views.project_change_status, name='project_change_status'),
    path('<int:pk>/tasks/', tasks_views.project_tasks, name='project_tasks'),
    path('<int:pk>/tasks/new/', tasks_views.task_create, name='task_create'),
    path('<int:pk>/timesheet/', budget_views.project_timesheet, name='project_timesheet'),
    path('<int:pk>/budget/', budget_views.project_budget, name='project_budget'),
    path('<int:pk>/budget/category/new/', budget_views.budget_category_create, name='budget_category_create'),
    path('<int:pk>/budget/category/<int:cat_pk>/edit/', budget_views.budget_category_edit, name='budget_category_edit'),
    path('<int:pk>/budget/category/<int:cat_pk>/delete/', budget_views.budget_category_delete, name='budget_category_delete'),
    path('<int:project_pk>/requirements/', req_views.project_requirements, name='project_requirements'),
    path('<int:project_pk>/requirements/new/', req_views.requirement_create, name='requirement_create'),
    path('<int:project_pk>/requirements/<int:pk>/edit/', req_views.requirement_edit, name='requirement_edit'),
    path('<int:project_pk>/requirements/<int:pk>/delete/', req_views.requirement_delete, name='requirement_delete'),
    path('<int:project_pk>/wbs/', req_views.project_wbs, name='project_wbs'),
    path('<int:project_pk>/wbs/new/', req_views.wbs_create, name='wbs_create'),
    path('<int:project_pk>/wbs/<int:pk>/edit/', req_views.wbs_edit, name='wbs_edit'),
    path('<int:project_pk>/wbs/<int:pk>/delete/', req_views.wbs_delete, name='wbs_delete'),
    path('<int:project_pk>/wbs/<int:pk>/move/', req_views.wbs_move, name='wbs_move'),
    path('<int:pk>/report/', report_views.pm_project_report, name='pm_project_report'),
    path('<int:project_pk>/requirements/report/', report_views.analyst_requirements_report, name='analyst_requirements_report'),
]

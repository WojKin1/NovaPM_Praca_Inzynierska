from django.urls import path

from . import views

urlpatterns = [
    path('', views.my_timesheet, name='my_timesheet'),
    path('add/', views.timesheet_add, name='timesheet_add'),
    path('<int:pk>/edit/', views.timesheet_edit, name='timesheet_edit'),
    path('<int:pk>/delete/', views.timesheet_delete, name='timesheet_delete'),
    path('<int:pk>/approve/', views.timesheet_approve, name='timesheet_approve'),
    path('<int:pk>/reject/', views.timesheet_reject, name='timesheet_reject'),
    path('<int:pk>/revoke/', views.timesheet_revoke_approval, name='timesheet_revoke_approval'),
]

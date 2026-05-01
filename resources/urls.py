from django.urls import path

from . import views

urlpatterns = [
    path('', views.member_add, name='member_add'),
    path('<int:member_pk>/remove/', views.member_remove, name='member_remove'),
    path('rates/', views.project_team_rates, name='project_team_rates'),
    path('<int:member_pk>/rate/', views.member_edit_rate, name='member_edit_rate'),
]

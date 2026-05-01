from django.urls import path

from . import views

urlpatterns = [
    path('', views.my_requirements_projects, name='my_requirements_projects'),
]

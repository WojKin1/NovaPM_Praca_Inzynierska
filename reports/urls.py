from django.urls import path

from . import views

urlpatterns = [
    path('', views.reports_index, name='reports_index'),
    path('developer/', views.developer_report, name='developer_report'),
    path('tester/', views.tester_report, name='tester_report'),
]

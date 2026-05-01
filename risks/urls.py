from django.urls import path

from . import views

urlpatterns = [
    path('', views.risk_list, name='risk_list'),
    path('new/', views.risk_create, name='risk_create'),
    path('<int:pk>/edit/', views.risk_edit, name='risk_edit'),
    path('<int:pk>/close/', views.risk_close, name='risk_close'),
]

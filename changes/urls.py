from django.urls import path

from . import views

urlpatterns = [
    path('', views.cr_list, name='cr_list'),
    path('new/', views.cr_create, name='cr_create'),
    path('<int:pk>/', views.cr_detail, name='cr_detail'),
    path('<int:pk>/submit/', views.cr_submit, name='cr_submit'),
]

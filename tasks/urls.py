from django.urls import path

from . import views

urlpatterns = [
    path('', views.my_tasks, name='my_tasks'),
    path('reviews/', views.my_reviews, name='my_reviews'),
    path('<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('<int:pk>/status/', views.task_change_status, name='task_change_status'),
    path('<int:pk>/review/', views.task_review, name='task_review'),
    path('<int:pk>/quick-status/', views.task_quick_status, name='task_quick_status'),
]

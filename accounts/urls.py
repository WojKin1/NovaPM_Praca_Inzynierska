from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # Profil
    path('profile/', views.user_profile, name='user_profile'),
    # Wymuszona zmiana hasła (pierwsze logowanie)
    path('password/change/', views.password_change_forced, name='password_change_forced'),
    # Reset hasła przez email
    path('password/reset/', views.password_reset_request, name='password_reset'),
    path(
        'password/reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/password/reset/done/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password/reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]

import logging
import threading

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

from .forms import EmailChangeForm, ForcePasswordChangeForm
from .models import User


class LoginView(auth_views.LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        role = self.request.user.role
        if role == User.Role.ADMIN:
            return '/admin/'
        if role == User.Role.PM:
            return '/projects/'
        if role == User.Role.ANALYST:
            return '/requirements/'
        if role == User.Role.DEVELOPER:
            return '/tasks/'
        if role == User.Role.TESTER:
            return '/tasks/reviews/'
        return '/dashboard/'


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


def _role_home_url(user):
    role = user.role
    if role == User.Role.ADMIN:
        return '/admin/'
    if role == User.Role.PM:
        return '/projects/'
    if role == User.Role.ANALYST:
        return '/requirements/'
    if role == User.Role.DEVELOPER:
        return '/tasks/'
    if role == User.Role.TESTER:
        return '/tasks/reviews/'
    return '/dashboard/'


@login_required
def password_change_forced(request):
    """Wymuszona zmiana hasła przy pierwszym logowaniu — nie wymaga starego hasła."""
    if not request.user.must_change_password:
        return redirect(_role_home_url(request.user))

    if request.method == 'POST':
        form = ForcePasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            request.user.must_change_password = False
            request.user.save(update_fields=['must_change_password'])
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Hasło zostało ustawione. Witaj w NovaPM!')
            return redirect(_role_home_url(request.user))
    else:
        form = ForcePasswordChangeForm(request.user)

    return render(request, 'accounts/force_password_change.html', {'form': form})


@login_required
def user_profile(request):
    """Strona profilu z dwiema kartami: zmiana emaila i zmiana hasła."""
    email_form = EmailChangeForm(request.user)
    password_form = PasswordChangeForm(request.user)
    active_tab = 'email'

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'change_email':
            active_tab = 'email'
            email_form = EmailChangeForm(request.user, request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data['email']
                request.user.save(update_fields=['email'])
                messages.success(request, 'Adres email został zmieniony.')
                return redirect('user_profile')

        elif action == 'change_password':
            active_tab = 'password'
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Hasło zostało zmienione.')
                return redirect('user_profile')

    return render(request, 'accounts/profile.html', {
        'email_form': email_form,
        'password_form': password_form,
        'active_tab': active_tab,
    })


def password_reset_request(request):
    """Formularz resetowania hasła przez email."""
    sent = False
    error = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        logger.info('Password reset requested for email: %r', email)

        if not email:
            error = 'Podaj adres email.'
        else:
            # Szukaj usera ignorując wielkość liter
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None
                logger.info('Password reset: no user found for email %r', email)
            except User.MultipleObjectsReturned:
                user = User.objects.filter(email__iexact=email).order_by('id').first()
                logger.warning('Password reset: multiple users for email %r, using pk=%s', email, user.pk)

            if user:
                logger.info('Password reset: found user %r (pk=%s)', user.username, user.pk)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirm', args=[uid, token])
                )
                logger.info('Password reset URL generated: %s', reset_url)

                subject = 'Resetowanie hasła — NovaPM'
                body = (
                    f'Witaj {user.get_full_name() or user.username},\n\n'
                    f'Kliknij w poniższy link, aby zresetować hasło:\n\n'
                    f'{reset_url}\n\n'
                    f'Link jest jednorazowy i wygasa po 24 godzinach.\n\n'
                    f'Jeśli nie prosiłeś/aś o reset hasła, zignoruj tę wiadomość.'
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient = [user.email]

                def _send(subj, msg, frm, to):
                    try:
                        send_mail(subj, msg, frm, to)
                        logger.info('Password reset email sent to %r', to)
                    except Exception as exc:
                        logger.error('Password reset email FAILED for %r: %s', to, exc, exc_info=True)

                threading.Thread(
                    target=_send,
                    args=(subject, body, from_email, recipient),
                    daemon=True,
                ).start()

            sent = True

    return render(request, 'accounts/password_reset.html', {'sent': sent, 'error': error})

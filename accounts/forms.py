from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm


class ForcePasswordChangeForm(SetPasswordForm):
    """Zmiana hasła bez podawania starego — używana przy pierwszym logowaniu."""
    pass


class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label='Nowy adres email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    current_password = forms.CharField(
        label='Aktualne hasło',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data.get('current_password')
        if not self.user.check_password(password):
            raise forms.ValidationError('Nieprawidłowe hasło.')
        return password

    def clean_email(self):
        email = self.cleaned_data.get('email')
        from .models import User
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Ten adres email jest już używany.')
        return email

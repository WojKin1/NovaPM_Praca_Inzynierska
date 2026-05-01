from django import forms

from accounts.models import User
from .models import ProjectMember

_SELECT = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'
_INPUT  = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'

_RATE_HELP = 'Pozostaw puste aby użyć domyślnej stawki dla roli (PM 200, Analityk 180, Developer 150, Tester 120 zł/h)'


class ProjectMemberForm(forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ['user', 'role_in_project', 'availability_percent', 'hourly_rate']
        widgets = {
            'user':                forms.Select(attrs={'class': _SELECT}),
            'role_in_project':     forms.Select(attrs={'class': _SELECT}),
            'availability_percent': forms.NumberInput(attrs={
                'class': _INPUT,
                'min': 10, 'max': 100, 'step': 5,
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': _INPUT,
                'min': '0', 'step': '0.01', 'placeholder': 'np. 150.00',
            }),
        }
        labels = {
            'user':                'Użytkownik',
            'role_in_project':     'Rola w projekcie',
            'availability_percent': 'Dostępność (%)',
            'hourly_rate':         'Stawka godzinowa (PLN)',
        }
        help_texts = {
            'hourly_rate': _RATE_HELP,
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        active_users = User.objects.filter(is_active_employee=True).order_by('username')
        if project is not None:
            existing_ids = project.members.filter(is_active=True).values_list('user_id', flat=True)
            active_users = active_users.exclude(pk__in=existing_ids)
        self.fields['user'].queryset = active_users

    def clean_hourly_rate(self):
        rate = self.cleaned_data.get('hourly_rate')
        if rate is not None and rate < 0:
            raise forms.ValidationError('Stawka nie może być ujemna.')
        return rate

    def clean_availability_percent(self):
        val = self.cleaned_data.get('availability_percent')
        if val is None:
            return val
        if val < 10 or val > 100:
            raise forms.ValidationError('Dostępność musi być w zakresie 10–100%.')
        return val

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get('user')
        if user and self.project:
            already = ProjectMember.objects.filter(
                project=self.project, user=user, is_active=True
            ).exists()
            if already:
                self.add_error('user', 'Ten użytkownik jest już aktywnym członkiem tego projektu.')
        return cleaned


class MemberRateForm(forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ['hourly_rate']
        widgets = {
            'hourly_rate': forms.NumberInput(attrs={
                'class': _INPUT,
                'min': '0', 'step': '0.01', 'placeholder': 'np. 150.00',
            }),
        }
        labels = {
            'hourly_rate': 'Stawka godzinowa (PLN)',
        }
        help_texts = {
            'hourly_rate': _RATE_HELP,
        }

    def clean_hourly_rate(self):
        rate = self.cleaned_data.get('hourly_rate')
        if rate is not None and rate < 0:
            raise forms.ValidationError('Stawka nie może być ujemna.')
        return rate

from django import forms

from accounts.models import User
from resources.models import ProjectMember
from .models import Task

_INPUT    = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-500'
_SELECT   = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'
_TEXTAREA = f'{_INPUT} resize-none'
_DATE     = f'{_INPUT} [color-scheme:dark]'


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'status', 'priority',
                  'due_date', 'estimated_hours']
        widgets = {
            'title':           forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Tytuł zadania'}),
            'description':     forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3, 'placeholder': 'Opis zadania'}),
            'assigned_to':     forms.Select(attrs={'class': _SELECT}),
            'status':          forms.Select(attrs={'class': _SELECT}),
            'priority':        forms.Select(attrs={'class': _SELECT}),
            'due_date':        forms.DateInput(attrs={'class': _DATE, 'type': 'date'}, format='%Y-%m-%d'),
            'estimated_hours': forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '0', 'min': '0', 'step': '0.5'}),
        }
        labels = {
            'title':           'Tytuł zadania',
            'description':     'Opis',
            'assigned_to':     'Przypisane do',
            'status':          'Status',
            'priority':        'Priorytet',
            'due_date':        'Termin wykonania',
            'estimated_hours': 'Szacowany czas (h)',
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            member_ids = ProjectMember.objects.filter(
                project=project, is_active=True
            ).values_list('user_id', flat=True)
            # Include PM too
            pm_id = project.project_manager_id
            user_qs = User.objects.filter(
                pk__in=list(member_ids) + [pm_id]
            ).order_by('username')
            self.fields['assigned_to'].queryset = user_qs
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(
                is_active_employee=True
            ).order_by('username')
        self.fields['assigned_to'].required = False


class TaskStatusForm(forms.Form):
    """Minimal form used by developer to update only status + actual_hours."""
    status = forms.ChoiceField(
        choices=Task.Status.choices,
        widget=forms.Select(attrs={'class': 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        label='Status',
    )
    actual_hours = forms.DecimalField(
        max_digits=6, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500', 'step': '0.5', 'min': '0'}),
        label='Rzeczywisty czas (h)',
    )

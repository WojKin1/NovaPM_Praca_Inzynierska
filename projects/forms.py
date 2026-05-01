from django import forms

from .models import Project

_INPUT  = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-500'
_SELECT = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'
_TEXTAREA = f'{_INPUT} resize-none'
_DATE = f'{_INPUT} [color-scheme:dark]'


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'client_name', 'description',
            'status', 'priority',
            'start_date', 'end_date',
            'budget_planned',
        ]
        widgets = {
            'name':           forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nazwa projektu'}),
            'client_name':    forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nazwa klienta'}),
            'description':    forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 5, 'placeholder': 'Opis projektu (opcjonalnie)'}),
            'status':         forms.Select(attrs={'class': _SELECT}),
            'priority':       forms.Select(attrs={'class': _SELECT}),
            'start_date':     forms.DateInput(attrs={'class': _DATE, 'type': 'date'}, format='%Y-%m-%d'),
            'end_date':       forms.DateInput(attrs={'class': _DATE, 'type': 'date'}, format='%Y-%m-%d'),
            'budget_planned': forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}),
        }
        labels = {
            'name':           'Nazwa projektu',
            'client_name':    'Klient',
            'description':    'Opis',
            'status':         'Status',
            'priority':       'Priorytet',
            'start_date':     'Data rozpoczęcia',
            'end_date':       'Data zakończenia',
            'budget_planned': 'Budżet planowany (zł)',
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end   = cleaned.get('end_date')
        budget = cleaned.get('budget_planned')

        if start and end and end <= start:
            self.add_error('end_date', 'Data zakończenia musi być późniejsza niż data rozpoczęcia.')

        if budget is not None and budget <= 0:
            self.add_error('budget_planned', 'Budżet musi być większy niż 0.')

        return cleaned

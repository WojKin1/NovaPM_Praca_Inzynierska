from django import forms

from .models import ChangeRequest

_INPUT    = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-500'
_SELECT   = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'
_TEXTAREA = f'{_INPUT} resize-none'


class ChangeRequestForm(forms.ModelForm):
    class Meta:
        model = ChangeRequest
        fields = ['title', 'description', 'impact_scope', 'impact_time', 'impact_cost']
        widgets = {
            'title':        forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Krótki tytuł zmiany'}),
            'description':  forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 4, 'placeholder': 'Szczegółowy opis wnioskowanej zmiany'}),
            'impact_scope': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 4, 'placeholder': 'Jakie obszary projektu obejmuje zmiana?'}),
            'impact_time':  forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '0', 'min': '0'}),
            'impact_cost':  forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }
        labels = {
            'title':        'Tytuł wniosku',
            'description':  'Opis zmiany',
            'impact_scope': 'Zakres wpływu',
            'impact_time':  'Wpływ na harmonogram (dni)',
            'impact_cost':  'Wpływ na budżet (PLN)',
        }


_DECISION_CHOICES = [
    ('', '— wybierz decyzję —'),
    (ChangeRequest.Status.APPROVED, 'Zatwierdź'),
    (ChangeRequest.Status.REJECTED, 'Odrzuć'),
]


class DecisionForm(forms.Form):
    status = forms.ChoiceField(
        choices=_DECISION_CHOICES,
        widget=forms.Select(attrs={'class': _SELECT}),
        label='Decyzja',
    )

    def clean_status(self):
        val = self.cleaned_data.get('status')
        if val not in (ChangeRequest.Status.APPROVED, ChangeRequest.Status.REJECTED):
            raise forms.ValidationError('Wybierz decyzję: Zatwierdź lub Odrzuć.')
        return val

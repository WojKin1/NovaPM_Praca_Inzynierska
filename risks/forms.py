from django import forms

from accounts.models import User
from .models import Risk

_INPUT    = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-500'
_SELECT   = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'
_TEXTAREA = f'{_INPUT} resize-none'

_SCORE_CHOICES = [
    (1, '1 — Bardzo niskie'),
    (2, '2 — Niskie'),
    (3, '3 — Średnie'),
    (4, '4 — Wysokie'),
    (5, '5 — Bardzo wysokie'),
]


class RiskForm(forms.ModelForm):
    probability = forms.ChoiceField(
        choices=_SCORE_CHOICES,
        widget=forms.Select(attrs={'class': _SELECT, 'id': 'id_probability'}),
        label='Prawdopodobieństwo',
    )
    impact = forms.ChoiceField(
        choices=_SCORE_CHOICES,
        widget=forms.Select(attrs={'class': _SELECT, 'id': 'id_impact'}),
        label='Wpływ',
    )

    class Meta:
        model = Risk
        fields = ['title', 'description', 'probability', 'impact', 'status', 'owner', 'mitigation_plan']
        widgets = {
            'title':           forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nazwa ryzyka'}),
            'description':     forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3, 'placeholder': 'Opis ryzyka'}),
            'status':          forms.Select(attrs={'class': _SELECT}),
            'owner':           forms.Select(attrs={'class': _SELECT}),
            'mitigation_plan': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3, 'placeholder': 'Plan reakcji / mitygacji'}),
        }
        labels = {
            'title':           'Nazwa ryzyka',
            'description':     'Opis',
            'status':          'Status',
            'owner':           'Właściciel ryzyka',
            'mitigation_plan': 'Plan mitygacji',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = User.objects.filter(is_active_employee=True).order_by('username')
        # Ensure int values are coerced for bound forms (ChoiceField returns str)
        if self.instance.pk:
            self.initial['probability'] = self.instance.probability
            self.initial['impact'] = self.instance.impact

    def clean_probability(self):
        return int(self.cleaned_data['probability'])

    def clean_impact(self):
        return int(self.cleaned_data['impact'])

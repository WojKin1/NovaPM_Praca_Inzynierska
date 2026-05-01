from django import forms

from .models import Requirement, WBSElement

_INPUT    = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-amber-500 placeholder-gray-500'
_SELECT   = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-amber-500'
_TEXTAREA = f'{_INPUT} resize-none'


class RequirementForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ['code', 'title', 'description', 'req_type', 'priority', 'status']
        widgets = {
            'code':         forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'np. REQ-001'}),
            'title':        forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Tytuł wymagania'}),
            'description':  forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 4, 'placeholder': 'Opis wymagania...'}),
            'req_type':     forms.Select(attrs={'class': _SELECT}),
            'priority':     forms.Select(attrs={'class': _SELECT}),
            'status':       forms.Select(attrs={'class': _SELECT}),
        }
        labels = {
            'code':        'Kod wymagania',
            'title':       'Tytuł',
            'description': 'Opis',
            'req_type':    'Typ wymagania',
            'priority':    'Priorytet',
            'status':      'Status',
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError('Kod wymagania jest wymagany.')
        qs = Requirement.objects.filter(project=self.project, code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'Wymaganie o kodzie {code} już istnieje w tym projekcie.')
        return code


class WBSElementForm(forms.ModelForm):
    class Meta:
        model = WBSElement
        fields = ['name', 'description', 'parent']
        widgets = {
            'name':        forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nazwa elementu'}),
            'description': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3, 'placeholder': 'Opis (opcjonalnie)...'}),
            'parent':      forms.Select(attrs={'class': _SELECT}),
        }
        labels = {
            'name':        'Nazwa elementu',
            'description': 'Opis',
            'parent':      'Element nadrzędny',
        }

    def __init__(self, *args, project=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.project = project
        qs = WBSElement.objects.filter(project=project).order_by('code')
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        self.fields['parent'].queryset = qs
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = '— (element główny)'

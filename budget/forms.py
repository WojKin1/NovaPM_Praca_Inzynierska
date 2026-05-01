from django import forms
from django.utils import timezone

from tasks.models import Task
from .models import BudgetCategory, Timesheet

_INPUT    = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-500'
_SELECT   = 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-indigo-500'
_TEXTAREA = f'{_INPUT} resize-none'
_DATE     = f'{_INPUT} [color-scheme:dark]'


class TimesheetForm(forms.ModelForm):
    class Meta:
        model = Timesheet
        fields = ['task', 'date', 'hours', 'description']
        widgets = {
            'task':        forms.Select(attrs={'class': _SELECT}),
            'date':        forms.DateInput(attrs={'class': _DATE, 'type': 'date'}, format='%Y-%m-%d'),
            'hours':       forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '0', 'min': '0.5', 'max': '24', 'step': '0.5'}),
            'description': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3, 'placeholder': 'Opis wykonanej pracy'}),
        }
        labels = {
            'task':        'Zadanie',
            'date':        'Data',
            'hours':       'Liczba godzin',
            'description': 'Opis',
        }

    def __init__(self, *args, user=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and project is not None:
            self.fields['task'].queryset = Task.objects.filter(
                project=project, assigned_to=user
            ).order_by('title')
        else:
            self.fields['task'].queryset = Task.objects.none()
        self.fields['task'].required = False

    def clean_hours(self):
        hours = self.cleaned_data.get('hours')
        if hours is not None:
            if hours <= 0:
                raise forms.ValidationError('Liczba godzin musi być większa niż 0.')
            if hours > 24:
                raise forms.ValidationError('Liczba godzin nie może przekraczać 24.')
        return hours

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date > timezone.localdate():
            raise forms.ValidationError('Data nie może być w przyszłości.')
        return date


class RejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:outline-none focus:ring-2 focus:ring-red-500 placeholder-gray-500 resize-none',
            'rows': 4,
            'placeholder': 'Opisz powód odrzucenia wpisu...',
        }),
        label='Powód odrzucenia',
    )

    def clean_rejection_reason(self):
        reason = self.cleaned_data.get('rejection_reason', '').strip()
        if not reason:
            raise forms.ValidationError('Powód odrzucenia jest wymagany.')
        return reason


class BudgetCategoryForm(forms.ModelForm):
    _NON_LABOUR = [
        (v, l) for v, l in BudgetCategory.CategoryType.choices if v != 'LABOUR'
    ]

    class Meta:
        model = BudgetCategory
        fields = ['name', 'category_type', 'planned_amount', 'spent_amount']
        widgets = {
            'name':           forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nazwa kategorii'}),
            'category_type':  forms.Select(attrs={'class': _SELECT}),
            'planned_amount': forms.NumberInput(attrs={'class': _INPUT, 'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
            'spent_amount':   forms.NumberInput(attrs={'class': _INPUT, 'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
        }
        labels = {
            'name':           'Nazwa kategorii',
            'category_type':  'Typ kategorii',
            'planned_amount': 'Kwota planowana (PLN)',
            'spent_amount':   'Kwota wydana (PLN)',
        }

    def __init__(self, *args, is_new=False, is_labour=False, **kwargs):
        super().__init__(*args, **kwargs)
        if is_new:
            self.fields['category_type'].choices = [('', '— Wybierz typ —')] + self._NON_LABOUR
            del self.fields['spent_amount']
        elif is_labour:
            del self.fields['category_type']
            del self.fields['spent_amount']
        else:
            self.fields['category_type'].choices = [('', '— Wybierz typ —')] + self._NON_LABOUR

    def clean_planned_amount(self):
        amount = self.cleaned_data.get('planned_amount')
        if amount is not None and amount < 0:
            raise forms.ValidationError('Kwota planowana nie może być ujemna.')
        return amount

import json

from django import forms
from django.utils.text import slugify

from employees.models import Employee
from leave.models import LeaveAttrOption, LeaveAttribute, LeaveType


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_id', 'first_name', 'last_name', 'email',
            'department', 'job_title', 'hire_date', 'status',
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'hire_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-input'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'


class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['name', 'description', 'color', 'is_active']
        widgets = {
            'color': forms.TextInput(
                attrs={'type': 'color', 'style': 'height:42px;width:80px;padding:2px;'}
            ),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['placeholder'] = 'e.g. Injury'
        self.fields['description'].widget.attrs['class'] = 'form-input'
        self.fields['description'].widget.attrs['placeholder'] = 'Short description shown on the dashboard card.'
        self.fields['color'].widget.attrs['class'] = 'form-input'

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get('name') or '').strip()
        if name:
            slug = slugify(name)
            base = slug or 'leave-type'
            candidate, n = base, 1
            qs = LeaveType.objects.filter(slug=candidate)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            while qs.exists():
                n += 1
                candidate = f'{base}-{n}'
                qs = LeaveType.objects.filter(slug=candidate)
            cleaned['slug'] = candidate
        return cleaned


class LeaveAttributeForm(forms.ModelForm):
    class Meta:
        model = LeaveAttribute
        fields = [
            'name', 'label', 'field_type', 'required', 'sort_order',
            'group', 'help_text', 'placeholder', 'default_value',
            'validation_rules', 'condition', 'is_active',
        ]
        widgets = {
            'validation_rules': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional. JSON, e.g. {"min": 1, "max": 30}',
            }),
            'condition': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Optional. JSON, e.g. {"depends_on": "injury_type", "operator": "equals", "value": "work_related"}',
            }),
            'help_text': forms.TextInput(attrs={'placeholder': 'Shown under the field in the leave form.'}),
            'placeholder': forms.TextInput(attrs={'placeholder': 'Input placeholder text.'}),
            'group': forms.TextInput(attrs={'placeholder': 'Section heading to group related fields (optional).'}),
        }

    def __init__(self, *args, leave_type=None, **kwargs):
        self.leave_type = leave_type
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = (
            'Leave blank to auto-generate from the label '
            '(e.g. "Medical certificate" → medical_certificate).'
        )
        self.fields['validation_rules'].help_text = (
            'number/date: {"min": .., "max": ..} · text: {"min_length": .., '
            '"max_length": .., "regex": ..} · file: {"max_size_mb": ..}'
        )
        self.fields['sort_order'].required = False
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-input'

    def clean(self):
        cleaned = super().clean()

        for field in ('validation_rules', 'condition'):
            value = cleaned.get(field)
            if isinstance(value, str) and value.strip():
                try:
                    cleaned[field] = json.loads(value)
                except json.JSONDecodeError as exc:
                    self.add_error(field, f'Invalid JSON: {exc}')
            elif not value or not str(value).strip():
                cleaned[field] = {}
            if not isinstance(cleaned.get(field), dict):
                self.add_error(field, 'Must be a JSON object, e.g. {}.')
                cleaned[field] = {}

        name = (cleaned.get('name') or '').strip().lower().replace(' ', '_')
        if not name:
            name = slugify(cleaned.get('label') or '') or 'field'
        cleaned['name'] = name

        if self.leave_type and LeaveAttribute.objects.filter(
            leave_type=self.leave_type, name=name
        ).exclude(pk=self.instance.pk).exists():
            self.add_error(
                'name',
                f'An attribute named "{name}" already exists for this leave type.',
            )

        if cleaned.get('field_type') not in ('select', 'multiselect'):
            # Options only matter for choice fields; drop the stale value so
            # an empty select default doesn't fail model validation.
            cleaned['default_value'] = cleaned.get('default_value') or ''

        return cleaned


class LeaveAttrOptionForm(forms.ModelForm):
    class Meta:
        model = LeaveAttrOption
        fields = ['label', 'value', 'sort_order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'
        self.fields['sort_order'].widget.attrs['style'] = 'width:90px'
        # The model default of 0 must not leak into the initial value, or a
        # blank extra row looks "changed" (default 0 vs empty input) and fails
        # validation as if the user had filled it in.
        self.fields['sort_order'].required = False
        self.fields['sort_order'].initial = None
        self.initial['sort_order'] = None

    def clean_sort_order(self):
        return self.cleaned_data.get('sort_order') or 0


LeaveAttrOptionFormSet = forms.inlineformset_factory(
    LeaveAttribute,
    LeaveAttrOption,
    form=LeaveAttrOptionForm,
    extra=1,
    can_delete=True,
    min_num=0,
)
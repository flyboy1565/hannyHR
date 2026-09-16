import json
import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
)

from .models import LeaveAttribute, LeaveAttributeValue

FIELD_TYPE_MAP = {
    'text': 'text',
    'textarea': 'textarea',
    'richtext': 'textarea',
    'number': 'number',
    'date': 'date',
    'boolean': 'boolean',
    'select': 'select',
    'multiselect': 'multiselect',
    'file': 'file',
}


def _widget_attrs(attribute, extra=None):
    """Combine base widget attributes (help text, placeholder, condition)."""
    attrs = {}
    if attribute.placeholder:
        attrs['placeholder'] = attribute.placeholder
    if attribute.field_type == 'richtext':
        attrs['data-richtext'] = 'true'
    if isinstance(attribute.condition, dict) and attribute.condition.get('depends_on'):
        cond = attribute.condition
        attrs['data-cond-depends-on'] = cond['depends_on']
        attrs['data-cond-operator'] = cond.get('operator', 'equals')
        attrs['data-cond-value'] = json.dumps(cond.get('value', ''))
        attrs['data-cond-action'] = cond.get('action', 'show')
    if extra:
        attrs.update(extra)
    return attrs


def _apply_validation_rules(field, rules, field_type):
    """Apply validation_rules JSON to a Django form field."""
    if not isinstance(rules, dict):
        return
    if field_type == 'number':
        minimum = rules.get('min')
        maximum = rules.get('max')
        if minimum is not None:
            field.validators.insert(
                0, MinValueValidator(float(minimum))
            )
        if maximum is not None:
            field.validators.insert(
                0, MaxValueValidator(float(maximum))
            )
    elif field_type == 'date':
        if rules.get('min'):
            field.validators.insert(
                0, MinDateValidator(rules['min'])
            )
        if rules.get('max'):
            field.validators.insert(
                0, MaxDateValidator(rules['max'])
            )
    elif field_type in ('text', 'textarea', 'richtext'):
        if rules.get('min_length') is not None:
            field.validators.insert(
                0, MinLengthValidator(int(rules['min_length']))
            )
        if rules.get('max_length') is not None:
            field.validators.insert(
                0, MaxLengthValidator(int(rules['max_length']))
            )
        if rules.get('regex'):
            field.validators.insert(
                0, RegexValidator(re.compile(rules['regex']))
            )
    elif field_type == 'file':
        max_mb = rules.get('max_size_mb')
        if max_mb is not None:
            max_bytes = int(max_mb) * 1024 * 1024
            field.validators.insert(0, MaxFileSizeValidator(max_bytes))


class MaxFileSizeValidator:
    """FileField validator limiting the uploaded file size."""

    def __init__(self, max_bytes):
        self.max_bytes = max_bytes

    def __call__(self, file):
        if getattr(file, 'size', 0) > self.max_bytes:
            raise ValidationError(
                f'File too large. Maximum allowed size is '
                f'{self.max_bytes // (1024 * 1024)} MB.'
            )


def _date_validator(value, bound, direction):
    from django.utils.dateparse import parse_date
    bound = parse_date(str(bound))
    if bound is None:
        return
    if direction == 'min' and value < bound:
        raise ValidationError(f'Date must be on or after {bound.isoformat()}.')
    if direction == 'max' and value > bound:
        raise ValidationError(f'Date must be on or before {bound.isoformat()}.')


def MinDateValidator(bound):
    return lambda value: _date_validator(value, bound, 'min')


def MaxDateValidator(bound):
    return lambda value: _date_validator(value, bound, 'max')


class LeaveDynamicForm(forms.Form):
    """A form whose fields are generated from LeaveAttribute definitions.

    Conditional attributes are still rendered so the browser can toggle
    visibility, but their values are discarded (and required errors dropped)
    unless their condition is satisfied by the submitted data.
    """

    def __init__(self, *args, attributes=None, existing_values=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.attributes = list(attributes or [])
        existing = existing_values or {}

        # Standard fields shared by every leave request. `employee` and
        # `leave_type` are hidden and set in the selection step; the views
        # re-validate their presence. summary and date range are regular
        # form fields.
        self.fields['employee'] = forms.IntegerField(
            required=False, widget=forms.HiddenInput()
        )
        self.fields['leave_type'] = forms.IntegerField(
            required=False, widget=forms.HiddenInput()
        )
        self.fields['summary'] = forms.CharField(
            label='Reason summary',
            required=False,
            max_length=255,
            widget=forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Short summary HR sees at a glance',
            }),
            help_text='e.g. "Fractured wrist while playing football on company night."',
        )
        self.fields['start_date'] = forms.DateField(
            label='From',
            widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        )
        self.fields['end_date'] = forms.DateField(
            label='To',
            widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        )

        for attribute in self.attributes:
            name = attribute.name
            label = attribute.label
            rules = attribute.validation_rules or {}
            required = attribute.required
            field = None

            if attribute.field_type in ('text', 'textarea', 'richtext'):
                widget = forms.Textarea(attrs=_widget_attrs(attribute)) \
                    if attribute.field_type in ('textarea', 'richtext') \
                    else forms.TextInput(attrs=_widget_attrs(attribute))
                field = forms.CharField(
                    label=label, required=required, widget=widget,
                    help_text=attribute.help_text,
                )
            elif attribute.field_type == 'number':
                field = forms.FloatField(
                    label=label, required=required,
                    widget=forms.NumberInput(attrs=_widget_attrs(attribute)),
                    help_text=attribute.help_text,
                )
            elif attribute.field_type == 'date':
                field = forms.DateField(
                    label=label, required=required,
                    widget=forms.DateInput(
                        attrs=_widget_attrs(attribute, {'type': 'date'}),
                    ),
                    help_text=attribute.help_text,
                )
            elif attribute.field_type == 'boolean':
                field = forms.BooleanField(
                    label=label, required=False,
                    widget=forms.CheckboxInput(attrs=_widget_attrs(attribute)),
                    help_text=attribute.help_text,
                )
            elif attribute.field_type in ('select', 'multiselect'):
                options = [(o.value, o.label) for o in attribute.options.all()]
                if attribute.field_type == 'select':
                    if required:
                        options = [('', '— Please select —')] + options
                    field = forms.ChoiceField(
                        label=label, required=required, choices=options,
                        widget=forms.Select(attrs=_widget_attrs(attribute)),
                        help_text=attribute.help_text,
                    )
                else:
                    field = forms.MultipleChoiceField(
                        label=label, required=required, choices=options,
                        widget=forms.CheckboxSelectMultiple(
                            attrs=_widget_attrs(attribute)
                        ),
                        help_text=attribute.help_text,
                    )
            elif attribute.field_type == 'file':
                field = forms.FileField(
                    label=label, required=required,
                    widget=forms.ClearableFileInput(attrs=_widget_attrs(attribute)),
                    help_text=attribute.help_text,
                )

            _apply_validation_rules(field, rules, attribute.field_type)

            # Pre-fill when editing an existing request.
            if name in existing:
                field.initial = existing[name]

            self.fields[name] = field

    def _condition_met(self, cleaned, attribute):
        cond = attribute.condition or {}
        depends_on = cond.get('depends_on')
        if not depends_on:
            return True
        actual = cleaned.get(depends_on)
        expected = cond.get('value')
        operator = cond.get('operator', 'equals')
        if operator == 'equals':
            return actual == expected
        if operator == 'not_equals':
            return actual != expected
        if operator == 'in':
            expected_list = expected or []
            if isinstance(actual, (list, tuple)):
                return bool(set(actual) & set(expected_list))
            return actual in expected_list
        return True

    def clean(self):
        cleaned = super().clean()

        if getattr(self, 'fields', None):
            attr_names = {attr.name for attr in self.attributes}
            visible = {
                attr.name
                for attr in self.attributes
                if self._condition_met(cleaned, attr)
            }
            for name in list(self.fields.keys()):
                if name in attr_names and name not in visible:
                    cleaned.pop(name, None)
                    self.errors.pop(name, None)

        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', 'End date cannot be before the start date.')
            cleaned.pop('end_date', None)

        return cleaned

    def validation_log(self):
        """Human-readable list of (label, error) for display in the template."""
        if not self.errors:
            return []
        by_attr = {attr.name: attr for attr in self.attributes}
        return [
            (by_attr[name].label, err)
            for name, err_list in self.errors.items()
            for err in err_list
            if name in by_attr
        ]


def values_for_request(request):
    """Return {attribute_name: value} for an existing LeaveRequest."""
    result = {}
    for value in request.attribute_values.select_related('attribute').all():
        attr = value.attribute
        if attr.field_type == 'file':
            # FileField.post_clean / initial handles instance-based files via
            # the widget; here we pass the existing file object.
            result[attr.name] = value.value_file
        elif attr.field_type == 'number':
            try:
                result[attr.name] = float(value.value_text)
            except (TypeError, ValueError):
                result[attr.name] = value.value_text
        elif attr.field_type == 'date':
            from django.utils.dateparse import parse_date
            result[attr.name] = parse_date(value.value_text) or value.value_text
        elif attr.field_type == 'boolean':
            result[attr.name] = value.value_text.lower() == 'true'
        elif attr.field_type == 'multiselect':
            try:
                result[attr.name] = json.loads(value.value_text or '[]')
            except json.JSONDecodeError:
                result[attr.name] = []
        else:
            result[attr.name] = value.value_text
    return result


def save_dynamic_values(request, form):
    """Persist cleaned form data as LeaveAttributeValue rows."""
    cleaned = form.cleaned_data
    for attribute in form.attributes:
        name = attribute.name
        if name not in cleaned:
            continue
        value, _ = LeaveAttributeValue.objects.get_or_create(
            request=request, attribute=attribute
        )
        if attribute.field_type == 'file':
            file_obj = cleaned[name]
            if file_obj:
                value.value_file = file_obj
                value.value_text = ''
            elif cleaned.get(name) is False:
                # ClearableFileInput unchecked -> user cleared the file.
                if value.value_file:
                    value.value_file.delete(save=False)
                value.value_file = None
                value.value_text = ''
        elif attribute.field_type == 'boolean':
            value.value_text = 'true' if cleaned[name] else 'false'
        elif attribute.field_type == 'multiselect':
            value.value_text = json.dumps(cleaned[name])
        elif cleaned[name] is None:
            value.value_text = ''
        else:
            value.value_text = str(cleaned[name])
        value.save()
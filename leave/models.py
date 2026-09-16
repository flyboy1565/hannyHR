import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from employees.models import Employee


class LeaveType(models.Model):
    """The entity dimension of the EAV pattern: a category of leave.

    Examples: Injury, Maternity, Paternity, Death in the Family.
    """

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        'Badge color', max_length=20, default='#3B82F6',
        help_text='Hex color used for the badge in the HR list.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveAttribute(models.Model):
    """The attribute dimension of the EAV pattern: a dynamic form field.

    HR defines which attributes belong to a leave type, whether they are
    required, how they behave (type, validation, conditional display).
    """

    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('textarea', 'Text Area'),
        ('richtext', 'Rich Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Yes / No'),
        ('select', 'Dropdown (single choice)'),
        ('multiselect', 'Multiple choice'),
        ('file', 'File Upload'),
    ]

    CONDITION_OPERATORS = [
        ('equals', 'Equals'),
        ('not_equals', 'Does not equal'),
        ('in', 'Is one of'),
    ]

    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name='attributes'
    )
    name = models.SlugField(
        max_length=120,
        help_text='Internal machine name, e.g. medical_certificate.',
    )
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    required = models.BooleanField(
        default=False, help_text='HR is required to complete this item.'
    )
    sort_order = models.PositiveIntegerField(default=0)
    help_text = models.CharField(max_length=300, blank=True)
    placeholder = models.CharField(max_length=200, blank=True)
    default_value = models.CharField(max_length=200, blank=True)
    group = models.CharField(
        max_length=120, blank=True,
        help_text='Section heading used to group related attributes in the form.',
    )
    validation_rules = models.JSONField(
        default=dict, blank=True,
        help_text=(
            'Optional JSON rules. number/date: {"min": ..., "max": ...}. '
            'text: {"min_length": ..., "max_length": ..., "regex": ...}. '
            'file: {"max_size_mb": ...}.'
        ),
    )
    condition = models.JSONField(
        default=dict, blank=True,
        help_text=(
            'Optional conditional display logic: '
            '{"depends_on": "<attribute name>", "operator": "equals|not_equals|in", '
            '"value": "x" or ["a","b"]}.'
        ),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']
        unique_together = [('leave_type', 'name')]
        verbose_name = 'Attribute'

    def __str__(self):
        return f'{self.leave_type.name} / {self.label}'

    @property
    def depends_on(self):
        return self.condition.get('depends_on') if isinstance(self.condition, dict) else None

    @property
    def has_conditional(self):
        return 'depends_on' in (self.condition or {})

    def clean(self):
        super().clean()
        if self.condition and 'depends_on' in self.condition:
            operator = self.condition.get('operator')
            if operator not in dict(self.CONDITION_OPERATORS):
                raise ValidationError(
                    {'condition': f'Unsupported condition operator: {operator}'}
                )
            if operator == 'in' and not isinstance(self.condition.get('value'), list):
                raise ValidationError(
                    {'condition': 'The "in" operator requires a list value.'}
                )

    def save(self, *args, **kwargs):
        self.name = self.name.strip().lower().replace(' ', '_')
        super().save(*args, **kwargs)


class LeaveAttrOption(models.Model):
    """Selectable options for select / multiselect attributes."""

    attribute = models.ForeignKey(
        LeaveAttribute, on_delete=models.CASCADE, related_name='options'
    )
    label = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.attribute.label}: {self.label}'


class LeaveRequest(models.Model):
    """The EAV entity instance: a single leave event for an employee."""

    STATUS_CHOICES = [
        ('in_progress', 'In progress'),
        ('completed', 'Completed'),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name='requests'
    )
    summary = models.CharField(
        'Reason summary', max_length=255, blank=True,
        help_text='Short summary HR sees at a glance.',
    )
    start_date = models.DateField('From')
    end_date = models.DateField('To')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='completed'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_leave_requests',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.employee} — {self.leave_type.name} ({self.start_date} → {self.end_date})'

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError('End date cannot be before the start date.')


class LeaveAttributeValue(models.Model):
    """The value dimension of the EAV pattern."""

    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name='attribute_values'
    )
    attribute = models.ForeignKey(LeaveAttribute, on_delete=models.CASCADE)
    value_text = models.TextField(blank=True)
    value_file = models.FileField(
        upload_to='leave/attachments/%Y/%m/', blank=True, null=True
    )

    class Meta:
        unique_together = [('request', 'attribute')]
        verbose_name = 'Attribute Value'
        verbose_name_plural = 'Attribute Values'

    def __str__(self):
        return f'{self.request}: {self.attribute.label}'

    @property
    def display_value(self):
        if self.attribute.field_type == 'file':
            return self.value_file.name if self.value_file else ''
        if self.attribute.field_type == 'boolean':
            return 'Yes' if self.value_text.lower() == 'true' else 'No'
        if self.attribute.field_type == 'multiselect':
            try:
                selected = json.loads(self.value_text or '[]')
            except json.JSONDecodeError:
                return self.value_text
            labels = {
                o.value: o.label
                for o in self.attribute.options.all()
            }
            return ', '.join(labels.get(v, v) for v in selected)
        if self.attribute.field_type in ('select',):
            option = self.attribute.options.filter(value=self.value_text).first()
            return option.label if option else self.value_text
        return self.value_text
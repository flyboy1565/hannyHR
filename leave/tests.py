import json
from itertools import count

from django import forms
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from employees.models import Employee
from leave.forms import (
    LeaveDynamicForm,
    save_dynamic_values,
    values_for_request,
)
from leave.models import (
    LeaveAttrOption,
    LeaveAttribute,
    LeaveAttributeValue,
    LeaveRequest,
    LeaveType,
)

_type_counter = count(1)


def make_leave_type():
    n = next(_type_counter)
    return LeaveType.objects.create(
        name=f'Test Type {n}', slug=f'test-type-{n}', color='#EF4444'
    )


def make_employee():
    return Employee.objects.create(
        employee_id='EMP-1', first_name='Alice', last_name='Moyo',
        department='Engineering', status='active',
    )


def attr(leave_type, name, field_type, required=False, condition=None, rules=None):
    return LeaveAttribute.objects.create(
        leave_type=leave_type, name=name, label=name.replace('_', ' ').title(),
        field_type=field_type, required=required,
        condition=condition or {}, validation_rules=rules or {},
    )


class DynamicFormTests(TestCase):
    def setUp(self):
        self.leave_type = make_leave_type()

    def test_field_type_mapping(self):
        attr(self.leave_type, 'note', 'text', required=True)
        attr(self.leave_type, 'body', 'textarea')
        attr(self.leave_type, 'salary', 'number', required=True)
        attr(self.leave_type, 'start', 'date', required=True)
        attr(self.leave_type, 'was_on_site', 'boolean')
        attr(self.leave_type, 'doc', 'file')
        attrs = list(self.leave_type.attributes.all())

        form = LeaveDynamicForm(attributes=attrs)
        self.assertIsInstance(form.fields['note'], forms.CharField)
        self.assertIsInstance(form.fields['body'], forms.CharField)
        self.assertIsInstance(form.fields['salary'], forms.FloatField)
        self.assertIsInstance(form.fields['start'], forms.DateField)
        self.assertIsInstance(form.fields['was_on_site'], forms.BooleanField)
        self.assertIsInstance(form.fields['doc'], forms.FileField)
        self.assertTrue(form.fields['salary'].required)
        self.assertFalse(form.fields['was_on_site'].required)

    def test_select_and_multiselect_resolve(self):
        sel = attr(self.leave_type, 'level', 'select', required=True)
        LeaveAttrOption.objects.create(attribute=sel, label='Severe', value='severe')
        LeaveAttrOption.objects.create(attribute=sel, label='Minor', value='minor')
        multi = attr(self.leave_type, 'symptoms', 'multiselect')
        LeaveAttrOption.objects.create(attribute=multi, label='Pain', value='pain')
        LeaveAttrOption.objects.create(attribute=multi, label='Swelling', value='swelling')

        form = LeaveDynamicForm(attributes=list(self.leave_type.attributes.all()))
        choices = form.fields['level'].choices
        self.assertIn(('severe', 'Severe'), choices)
        # Required selects get a blank placeholder choice:
        self.assertEqual(choices[0][0], '')
        self.assertEqual(
            [v for v, _ in form.fields['symptoms'].choices],
            ['pain', 'swelling'],
        )

    def test_conditional_required_is_ignored_when_hidden(self):
        leave_type = make_leave_type()
        type_attr = attr(leave_type, 'type', 'select', required=True)
        LeaveAttrOption.objects.create(attribute=type_attr, label='Home', value='home')
        LeaveAttrOption.objects.create(attribute=type_attr, label='Work', value='work')
        condition = {'depends_on': 'type', 'operator': 'equals', 'value': 'work'}
        attr(leave_type, 'report_no', 'text', required=True, condition=condition)

        form = LeaveDynamicForm(data={
            'type': 'home',
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, attributes=list(leave_type.attributes.all()))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn('report_no', form.cleaned_data)

    def test_conditional_required_is_enforced_when_visible(self):
        leave_type = make_leave_type()
        type_attr = attr(leave_type, 'type', 'select', required=True)
        LeaveAttrOption.objects.create(attribute=type_attr, label='Home', value='home')
        LeaveAttrOption.objects.create(attribute=type_attr, label='Work', value='work')
        condition = {'depends_on': 'type', 'operator': 'equals', 'value': 'work'}
        attr(leave_type, 'report_no', 'text', required=True, condition=condition)

        # report_no is visible (type == work) but left blank → invalid.
        form = LeaveDynamicForm(data={
            'type': 'work',
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, attributes=list(leave_type.attributes.all()))
        self.assertFalse(form.is_valid())
        self.assertIn('report_no', form.errors)

    def test_multiselect_condition_in_operator(self):
        leave_type = make_leave_type()
        attr(leave_type, 'kind', 'multiselect', required=True)
        option = LeaveAttrOption.objects.create(
            attribute=leave_type.attributes.get(name='kind'),
            label='Sports', value='sports',
        )
        condition = {'depends_on': 'kind', 'operator': 'in', 'value': ['sports']}
        attr(leave_type, 'team_name', 'text', required=True, condition=condition)

        form = LeaveDynamicForm(data={
            'kind': ['sports'],
            'team_name': 'Crackers',
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, attributes=list(leave_type.attributes.all()))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('team_name', form.cleaned_data)

    def test_validation_rules_applied(self):
        attr(self.leave_type, 'days', 'number', required=True, rules={'min': 1, 'max': 30})
        form = LeaveDynamicForm(data={
            'days': '60',
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, attributes=list(self.leave_type.attributes.all()))
        self.assertFalse(form.is_valid())
        self.assertIn('days', form.errors)


class SaveRoundTripTests(TestCase):
    def setUp(self):
        self.leave_type = make_leave_type()
        self.employee = make_employee()
        attr(self.leave_type, 'note', 'text', required=True)
        multi = attr(self.leave_type, 'tags', 'multiselect')
        LeaveAttrOption.objects.create(attribute=multi, label='A', value='a')
        LeaveAttrOption.objects.create(attribute=multi, label='B', value='b')

    def test_save_and_reload(self):
        request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date='2026-01-01',
            end_date='2026-01-02',
        )
        form = LeaveDynamicForm(data={
            'note': 'Fractured wrist',
            'tags': ['a', 'b'],
            'start_date': '2026-01-01',
            'end_date': '2026-01-02',
        }, attributes=list(self.leave_type.attributes.all()))
        self.assertTrue(form.is_valid(), form.errors)
        save_dynamic_values(request, form)

        self.assertEqual(request.attribute_values.count(), 2)
        values = values_for_request(request)
        self.assertEqual(values['note'], 'Fractured wrist')
        self.assertEqual(values['tags'], ['a', 'b'])

        note = request.attribute_values.get(attribute__name='note')
        self.assertEqual(note.display_value, 'Fractured wrist')


class ViewFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            'hr', 'hr@example.com', 'pw'
        )
        self.client = Client()
        self.client.login(username='hr', password='pw')
        self.leave_type = make_leave_type()
        self.employee = make_employee()
        injury_type = attr(self.leave_type, 'injury_type', 'select', required=True)
        LeaveAttrOption.objects.create(attribute=injury_type, label='Work', value='work')
        attr(self.leave_type, 'where', 'text', required=True)

    def test_dashboard_requires_login(self):
        anon = Client()
        response = anon.get(reverse('leave:leave_type_list'))
        self.assertEqual(response.status_code, 302)

    def test_create_request_flow(self):
        url = reverse('leave:request_new')
        response = self.client.get(url)
        self.assertContains(response, 'name="employee"')

        response = self.client.get(
            url, {'employee': self.employee.pk, 'type': self.leave_type.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'injury_type')

        response = self.client.post(url, {
            'employee': self.employee.pk,
            'leave_type': self.leave_type.pk,
            'summary': 'Fractured wrist',
            'start_date': '2026-01-05',
            'end_date': '2026-01-09',
            'injury_type': 'work',
            'where': 'Site B',
        })
        request = LeaveRequest.objects.get()
        self.assertEqual(request.summary, 'Fractured wrist')
        self.assertEqual(
            request.attribute_values.get(attribute__name='where').value_text,
            'Site B',
        )
        self.assertRedirects(response, reverse('leave:leave_detail', args=[request.pk]))

    def test_edit_preserves_existing_values(self):
        request = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            summary='original',
            start_date='2026-01-05',
            end_date='2026-01-09',
        )
        LeaveAttributeValue.objects.create(
            request=request,
            attribute=self.leave_type.attributes.get(name='where'),
            value_text='Original text',
        )
        response = self.client.get(reverse('leave:request_edit', args=[request.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Original text')

        response = self.client.post(
            reverse('leave:request_edit', args=[request.pk]),
            {
                'employee': self.employee.pk,
                'leave_type': self.leave_type.pk,
                'summary': 'updated',
                'start_date': '2026-01-05',
                'end_date': '2026-01-10',
                'injury_type': 'work',
                'where': 'Changed',
            },
        )
        request.refresh_from_db()
        self.assertEqual(request.summary, 'updated')
        self.assertEqual(
            request.attribute_values.get(attribute__name='where').value_text,
            'Changed',
        )
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from employees.models import Employee
from leave.models import LeaveAttrOption, LeaveAttribute, LeaveRequest, LeaveType

User = get_user_model()


class HRConsoleAccessTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        url = reverse('hr:dashboard')
        response = self.client.get(url)
        self.assertIn(response.status_code, (302, 403))

    def test_plain_user_forbidden(self):
        User.objects.create_user('regular', 'r@example.com', 'pw')
        self.client.login(username='regular', password='pw')
        self.assertEqual(self.client.get(reverse('hr:dashboard')).status_code, 403)

    def test_hr_user_can_access_dashboard(self):
        user = User.objects.create_user('ops', 'ops@example.com', 'pw')
        from django.contrib.auth.models import Permission
        user.user_permissions.add(
            Permission.objects.get(codename='can_manage_hr')
        )
        self.client.login(username='ops', password='pw')
        self.assertEqual(self.client.get(reverse('hr:dashboard')).status_code, 200)


class EmployeeCrudTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('ops', 'ops@example.com', 'pw')
        from django.contrib.auth.models import Permission
        user.user_permissions.add(
            Permission.objects.get(codename='can_manage_hr')
        )
        self.client.login(username='ops', password='pw')

    def test_employee_list_and_search(self):
        Employee.objects.create(
            employee_id='EMP-1', first_name='Alice', last_name='Moyo',
            department='Engineering',
        )
        Employee.objects.create(
            employee_id='EMP-2', first_name='Bob', last_name='Allan',
            department='Design',
        )
        response = self.client.get(reverse('hr:employee_list'))
        self.assertContains(response, 'Alice')
        self.assertContains(response, 'Bob')

        response = self.client.get(
            reverse('hr:employee_list'), {'q': 'Emily'}
        )
        self.assertNotContains(response, 'Alice ')

    def test_employee_create(self):
        response = self.client.post(reverse('hr:employee_add'), {
            'employee_id': 'EMP-9',
            'first_name': 'Cara',
            'last_name': 'Zulu',
            'email': 'cara@example.com',
            'department': 'Finance',
            'job_title': 'Analyst',
            'hire_date': '2024-01-15',
            'status': 'active',
        }, follow=True)
        self.assertContains(response, 'Cara Zulu')
        self.assertTrue(Employee.objects.filter(employee_id='EMP-9').exists())

    def test_employee_edit(self):
        emp = Employee.objects.create(
            employee_id='EMP-3', first_name='Dan', last_name='Okon',
            department='Engineering',
        )
        response = self.client.post(
            reverse('hr:employee_edit', args=[emp.pk]),
            {
                'employee_id': 'EMP-3',
                'first_name': 'Daniel',
                'last_name': 'Okon',
                'status': 'active',
            },
            follow=True,
        )
        emp.refresh_from_db()
        self.assertEqual(emp.first_name, 'Daniel')
        self.assertContains(response, 'Daniel')

    def test_employee_delete_plain(self):
        emp = Employee.objects.create(
            employee_id='EMP-4', first_name='Ed', last_name='Kane',
            department='Ops',
        )
        self.client.post(reverse('hr:employee_delete', args=[emp.pk]), {})
        self.assertFalse(Employee.objects.filter(pk=emp.pk).exists())

    def test_employee_delete_blocked_by_leave_records(self):
        emp = Employee.objects.create(
            employee_id='EMP-5', first_name='Fay', last_name='Ross',
            department='Ops',
        )
        leave_type = LeaveType.objects.create(
            name='Sick', slug='sick', color='#000000'
        )
        LeaveRequest.objects.create(
            employee=emp, leave_type=leave_type,
            start_date='2024-01-01', end_date='2024-01-03',
        )
        self.client.post(reverse('hr:employee_delete', args=[emp.pk]), {})
        self.assertTrue(Employee.objects.filter(pk=emp.pk).exists())


class LeaveTypeAndAttributeTests(TestCase):
    def setUp(self):
        user = User.objects.create_user('ops', 'ops@example.com', 'pw')
        from django.contrib.auth.models import Permission
        user.user_permissions.add(
            Permission.objects.get(codename='can_manage_hr')
        )
        self.client.login(username='ops', password='pw')

    def test_leavetype_create_and_detail(self):
        response = self.client.post(reverse('hr:leavetype_add'), {
            'name': 'Injury',
            'description': 'Physical injury leave.',
            'color': '#EF4444',
            'is_active': 'on',
        }, follow=True)
        self.assertEqual(LeaveType.objects.count(), 1)
        leave_type = LeaveType.objects.get(name='Injury')
        self.assertRedirects(response, reverse('hr:leavetype_detail', args=[leave_type.pk]))

    def test_attribute_create_with_options(self):
        leave_type = LeaveType.objects.create(
            name='Injury', slug='injury', color='#EF4444'
        )
        response = self.client.post(
            reverse('hr:attribute_add', args=[leave_type.pk]),
            {
                'name': 'injury_type',
                'label': 'Injury type',
                'field_type': 'select',
                'required': 'on',
                'is_active': 'on',
                'validation_rules': '{"min": 1}',
                'options-TOTAL_FORMS': '2',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-label': 'Work related',
                'options-0-value': 'work_related',
                'options-0-sort_order': '0',
                'options-0-attribute': '',
                'options-0-id': '',
                'options-1-label': 'Home',
                'options-1-value': 'home',
                'options-1-sort_order': '1',
                'options-1-attribute': '',
                'options-1-id': '',
            },
        )
        attribute = LeaveAttribute.objects.get(leave_type=leave_type, name='injury_type')
        self.assertRedirects(
            response, reverse('hr:leavetype_detail', args=[leave_type.pk])
        )
        self.assertEqual(
            list(attribute.options.values_list('value', flat=True)),
            ['work_related', 'home'],
        )
        self.assertEqual(attribute.validation_rules, {'min': 1})

    def test_attribute_create_rolls_back_on_bad_options(self):
        leave_type = LeaveType.objects.create(
            name='Injury', slug='injury', color='#EF4444'
        )
        response = self.client.post(
            reverse('hr:attribute_add', args=[leave_type.pk]),
            {
                'name': '',
                'label': 'Injury type',
                'field_type': 'select',
                'is_active': 'on',
                'options-TOTAL_FORMS': '1',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-label': '',
                'options-0-value': '',
                'options-0-sort_order': '0',
                'options-0-attribute': '',
                'options-0-id': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LeaveAttribute.objects.count(), 0)

    def test_attribute_edit_updates_options(self):
        leave_type = LeaveType.objects.create(
            name='Injury', slug='injury', color='#EF4444'
        )
        attribute = LeaveAttribute.objects.create(
            leave_type=leave_type, name='severity', label='Severity',
            field_type='select',
        )
        LeaveAttrOption.objects.create(
            attribute=attribute, label='Minor', value='minor'
        )
        self.client.post(
            reverse('hr:attribute_edit', args=[leave_type.pk, attribute.pk]),
            {
                'name': 'severity',
                'label': 'Severity level',
                'field_type': 'select',
                'is_active': 'on',
                'options-TOTAL_FORMS': '2',
                'options-INITIAL_FORMS': '1',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-label': 'Moderate',
                'options-0-value': 'moderate',
                'options-0-sort_order': '0',
                'options-0-attribute': str(attribute.pk),
                'options-0-id': str(LeaveAttrOption.objects.get().pk),
                'options-1-label': '',
                'options-1-value': '',
                'options-1-sort_order': '',
                'options-1-attribute': str(attribute.pk),
                'options-1-id': '',
            },
        )
        attribute.refresh_from_db()
        self.assertEqual(attribute.label, 'Severity level')
        self.assertEqual(
            list(attribute.options.values_list('value', flat=True)),
            ['moderate'],
        )

    def test_attribute_delete(self):
        leave_type = LeaveType.objects.create(
            name='Injury', slug='injury', color='#EF4444'
        )
        attribute = LeaveAttribute.objects.create(
            leave_type=leave_type, name='notes', label='Notes',
            field_type='textarea',
        )
        option = LeaveAttrOption.objects.create(
            attribute=attribute, label='X', value='x'
        )
        self.client.post(
            reverse('hr:attribute_delete', args=[leave_type.pk, attribute.pk]),
            {},
        )
        self.assertFalse(LeaveAttribute.objects.filter(pk=attribute.pk).exists())
        self.assertFalse(LeaveAttrOption.objects.filter(pk=option.pk).exists())
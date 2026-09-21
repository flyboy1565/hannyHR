from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission, User

from employees.models import Employee
from leave.models import (
    LeaveAttrOption,
    LeaveAttribute,
    LeaveAttributeValue,
    LeaveRequest,
    LeaveType,
)


class Command(BaseCommand):
    help = 'Seed demo leave types, attributes, and sample employees.'

    def handle(self, *args, **options):
        UserModel = get_user_model()
        if not UserModel.objects.filter(username='hr').exists():
            UserModel.objects.create_superuser('hr', 'hr@example.com', 'hannyhr123')

        # Create groups
        supervisor_group, _ = Group.objects.get_or_create(name='HR Supervisor')
        team_member_group, _ = Group.objects.get_or_create(name='HR Team Member')

        # Supervisor permissions: can_manage_hr, can_hijack_users, leave CRUD
        supervisor_perms = Permission.objects.filter(
            codename__in=[
                'can_manage_hr', 'can_hijack_users', 'can_view_team_portal',
                'add_leaverequest', 'view_leaverequest', 'change_leaverequest',
            ]
        )
        supervisor_group.permissions.set(supervisor_perms)

        # Team Member permissions: can_view_team_portal, leave CRUD
        team_member_perms = Permission.objects.filter(
            codename__in=[
                'can_view_team_portal',
                'add_leaverequest', 'view_leaverequest', 'change_leaverequest',
            ]
        )
        team_member_group.permissions.set(team_member_perms)

        # HR Supervisor user: hr.supervisor / supervisor123
        if not UserModel.objects.filter(username='hr.supervisor').exists():
            supervisor = UserModel.objects.create_user(
                'hr.supervisor', 'hr.supervisor@example.com', 'supervisor123'
            )
            supervisor.groups.add(supervisor_group)
        else:
            supervisor = UserModel.objects.get(username='hr.supervisor')
            supervisor.groups.add(supervisor_group)

        # HR Team Member user: hr.ops / hroperations123
        if not UserModel.objects.filter(username='hr.ops').exists():
            ops = UserModel.objects.create_user(
                'hr.ops', 'hr.ops@example.com', 'hroperations123'
            )
            ops.groups.add(team_member_group)
        else:
            ops = UserModel.objects.get(username='hr.ops')
            ops.groups.add(team_member_group)

        # Regular employee user: alice / alice123
        if not UserModel.objects.filter(username='alice').exists():
            alice = UserModel.objects.create_user(
                'alice', 'alice@example.com', 'alice123'
            )
        else:
            alice = UserModel.objects.get(username='alice')

        employees = [
            # Engineering
            {'employee_id': 'EMP-1001', 'first_name': 'Alice', 'last_name': 'Moyo',
             'department': 'Engineering', 'job_title': 'Backend Engineer'},
            {'employee_id': 'EMP-1002', 'first_name': 'Ben', 'last_name': 'Kariuki',
             'department': 'Engineering', 'job_title': 'Product Designer'},
            {'employee_id': 'EMP-1003', 'first_name': 'Clara', 'last_name': 'Okafor',
             'department': 'Engineering', 'job_title': 'DevOps Engineer'},
            {'employee_id': 'EMP-1004', 'first_name': 'David', 'last_name': 'Zulu',
             'department': 'Engineering', 'job_title': 'Frontend Engineer'},
            {'employee_id': 'EMP-1005', 'first_name': 'Esther', 'last_name': 'Nwosu',
             'department': 'Engineering', 'job_title': 'Data Engineer'},
            {'employee_id': 'EMP-1006', 'first_name': 'Frank', 'last_name': 'Adeyemi',
             'department': 'Engineering', 'job_title': 'DevOps Engineer'},
            # Design
            {'employee_id': 'EMP-1007', 'first_name': 'Grace', 'last_name': 'Banda',
             'department': 'Design', 'job_title': 'Brand Designer'},
            {'employee_id': 'EMP-1008', 'first_name': 'Henry', 'last_name': 'Mwangi',
             'department': 'Design', 'job_title': 'Product Designer'},
            {'employee_id': 'EMP-1009', 'first_name': 'Imani', 'last_name': 'Osei',
             'department': 'Design', 'job_title': 'UX Designer'},
            {'employee_id': 'EMP-1010', 'first_name': 'James', 'last_name': 'Diallo',
             'department': 'Design', 'job_title': 'Design Lead'},
            # Product / Data
            {'employee_id': 'EMP-1012', 'first_name': 'Kevin', 'last_name': 'Ondiek',
             'department': 'Product', 'job_title': 'Product Manager'},
            {'employee_id': 'EMP-1013', 'first_name': 'Linda', 'last_name': 'Chikwanda',
             'department': 'Product', 'job_title': 'Associate Product Manager'},
            {'employee_id': 'EMP-1017', 'first_name': 'Priya', 'last_name': 'Nair',
             'department': 'Data', 'job_title': 'Data Analyst'},
            {'employee_id': 'EMP-1018', 'first_name': 'Quinn', 'last_name': 'Adeola',
             'department': 'Data', 'job_title': 'ML Engineer'},
            # Finance / People Ops
            {'employee_id': 'EMP-1019', 'first_name': 'Rachel', 'last_name': 'Zimba',
             'department': 'Finance', 'job_title': 'Finance Manager'},
            {'employee_id': 'EMP-1020', 'first_name': 'Samuel', 'last_name': 'Ochieng',
             'department': 'Finance', 'job_title': 'Payroll Specialist'},
            {'employee_id': 'EMP-1021', 'first_name': 'Tina', 'last_name': 'Falana',
             'department': 'People Ops', 'job_title': 'HR Business Partner'},
            {'employee_id': 'EMP-1022', 'first_name': 'Usman', 'last_name': 'Garba',
             'department': 'People Ops', 'job_title': 'Recruiter'},
            # Sales / Marketing / Support
            {'employee_id': 'EMP-1023', 'first_name': 'Vera', 'last_name': 'Kiprop',
             'department': 'Sales', 'job_title': 'Account Executive'},
            {'employee_id': 'EMP-1024', 'first_name': 'William', 'last_name': 'Otieno',
             'department': 'Sales', 'job_title': 'Sales Manager'},
            {'employee_id': 'EMP-1025', 'first_name': 'Ximena', 'last_name': 'Rojas',
             'department': 'Marketing', 'job_title': 'Marketing Associate'},
            {'employee_id': 'EMP-1026', 'first_name': 'Yusuf', 'last_name': 'Ali',
             'department': 'Marketing', 'job_title': 'Social Media Manager'},
            {'employee_id': 'EMP-1027', 'first_name': 'Zoe', 'last_name': 'Hassan',
             'department': 'Support', 'job_title': 'Support Engineer'},
            {'employee_id': 'EMP-1028', 'first_name': 'Adam', 'last_name': 'Kamau',
             'department': 'Support', 'job_title': 'Customer Success Manager'},
            # Operations / Leadership
            {'employee_id': 'EMP-1029', 'first_name': 'Brenda', 'last_name': 'Musoke',
             'department': 'Operations', 'job_title': 'Operations Manager'},
            {'employee_id': 'EMP-1030', 'first_name': 'Caleb', 'last_name': 'Njoroge',
             'department': 'Leadership', 'job_title': 'Head of Engineering'},
            {'employee_id': 'EMP-1031', 'first_name': 'Thandi', 'last_name': 'Ndlovu',
             'department': 'HR', 'job_title': 'HR Operations'},
            {'employee_id': 'EMP-1032', 'first_name': 'Sipho', 'last_name': 'Dlamini',
             'department': 'HR', 'job_title': 'HR Director'},
            {'employee_id': 'EMP-1033', 'first_name': 'Naledi', 'last_name': 'Mokoena',
             'department': 'HR', 'job_title': 'HR Supervisor'},
        ]
        for data in employees:
            Employee.objects.get_or_create(employee_id=data['employee_id'], defaults=data)

        # Link Alice to her employee record
        alice_emp = Employee.objects.get(employee_id='EMP-1001')
        if not alice_emp.user:
            alice_emp.user = alice
            alice_emp.save()
        # Give Alice portal access so she can see her own leave data
        portal_perm = Permission.objects.get(codename='can_view_team_portal')
        alice.user_permissions.add(portal_perm)

        # Link hr.ops to their employee record
        ops_emp = Employee.objects.get(employee_id='EMP-1031')
        if not ops_emp.user:
            ops_emp.user = ops
            ops_emp.save()

        # Link hr (superuser) to their employee record
        hr_user = UserModel.objects.get(username='hr')
        hr_emp = Employee.objects.get(employee_id='EMP-1032')
        if not hr_emp.user:
            hr_emp.user = hr_user
            hr_emp.save()

        # Link hr.supervisor to their employee record
        supervisor = UserModel.objects.get(username='hr.supervisor')
        sup_emp = Employee.objects.get(employee_id='EMP-1033')
        if not sup_emp.user:
            sup_emp.user = supervisor
            sup_emp.save()

        self.seed_injury()
        self.seed_maternity()
        self.seed_paternity()
        self.seed_bereavement()
        self.seed_leaves()
        self.stdout.write(self.style.SUCCESS('Demo data seeded.'))

    def seed_leaves(self):
        """Seed a handful of previous, completed leave records."""
        hr_user = User.objects.get(username='hr')
        self._leaf('EMP-1001', 'injury', 'Fell while cycling — broken right wrist.',
                   '2026-03-02', '2026-03-06',
                   values=[
                       ('injury_type', 'work_related'),
                       ('injury_occurred_at', '2026-03-02'),
                       ('body_part', 'Right wrist'),
                       ('severity', 'severe'),
                       ('workplace_accident_report', 'true'),
                       ('report_number', 'ACC-2026-014'),
                   ])
        self._leaf('EMP-1002', 'injury', 'Sprained ankle at home over the weekend.',
                   '2026-02-09', '2026-02-11',
                   values=[
                       ('injury_type', 'home'),
                       ('injury_occurred_at', '2026-02-07'),
                       ('body_part', 'Left ankle'),
                       ('severity', 'moderate'),
                   ])
        self._leaf('EMP-1017', 'maternity', 'Maternity leave around birth of first child.',
                   '2026-01-05', '2026-04-10',
                   values=[
                       ('due_date', '2026-02-01'),
                       ('baby_born_at', '2026-01-28'),
                       ('recovery_notes', 'Recovered well; cleared to return.'),
                   ])
        self._leaf('EMP-1003', 'paternity', 'Paternity leave for birth of daughter.',
                   '2026-06-15', '2026-06-19',
                   values=[
                       ('birth_date', '2026-06-14'),
                       ('relationship', 'biological'),
                       ('bonding_notes', 'Huge help around the house.'),
                   ])
        self._leaf('EMP-1004', 'death_in_family', 'Bereavement — loss of mother.',
                   '2026-07-20', '2026-07-24',
                   values=[
                       ('deceased_name', 'Mary Zulu'),
                       ('relationship', 'parent'),
                       ('funeral_date', '2026-07-23'),
                   ])
        self._leaf('EMP-1005', 'injury', 'Sports injury — dislocated shoulder.',
                   '2026-05-04', '2026-05-08',
                   values=[
                       ('injury_type', 'sports'),
                       ('injury_occurred_at', '2026-05-03'),
                       ('body_part', 'Left shoulder'),
                       ('severity', 'severe'),
                   ])
        self._leaf('EMP-1031', 'death_in_family', 'Loss of grandmother — family obligations.',
                   '2026-04-14', '2026-04-18',
                   values=[
                       ('deceased_name', 'Nokuthula Ndlovu'),
                       ('relationship', 'grandparent'),
                       ('funeral_date', '2026-04-17'),
                   ])
        self._leaf('EMP-1033', 'paternity', 'Paternity leave for birth of first child.',
                   '2026-08-04', '2026-08-08',
                   values=[
                       ('birth_date', '2026-08-03'),
                       ('relationship', 'biological'),
                       ('bonding_notes', 'Settling in nicely at home.'),
                   ])

    def _leaf(self, employee_id, type_slug, summary, start_date, end_date, values,
              status='completed'):
        employee = Employee.objects.get(employee_id=employee_id)
        leave_type = LeaveType.objects.get(slug=type_slug)
        request, created = LeaveRequest.objects.get_or_create(
            employee=employee, leave_type=leave_type,
            summary=summary, start_date=start_date,
            defaults={'end_date': end_date, 'status': status,
                      'created_by': User.objects.get(username='hr')},
        )
        for attr_name, text in values:
            attr = leave_type.attributes.get(name=attr_name)
            LeaveAttributeValue.objects.get_or_create(
                request=request, attribute=attr, defaults={'value_text': text},
            )

    def _type(self, name, slug, description, color):
        obj, created = LeaveType.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'description': description, 'color': color},
        )
        LeaveType.objects.filter(pk=obj.pk).update(name=name, color=color)
        return obj

    def _attr(self, leave_type, name, label, field_type, sort_order=0, required=False,
              group='', help_text='', rules=None, condition=None, options=None, **extra):
        defaults = {
            'label': label,
            'field_type': field_type,
            'sort_order': sort_order,
            'required': required,
            'group': group,
            'help_text': help_text,
            'validation_rules': rules or {},
            'condition': condition or {},
        }
        defaults.update(extra)
        attr, created = LeaveAttribute.objects.get_or_create(
            leave_type=leave_type, name=name, defaults=defaults,
        )
        if not created:
            for key, value in defaults.items():
                setattr(attr, key, value)
            attr.save()
        if options is not None:
            attr.options.all().delete()
            for sort, (opt_label, opt_value) in enumerate(options):
                self._option(attr, opt_label, opt_value, sort)
        return attr

    def _option(self, attr, label, value, sort_order=0):
        LeaveAttrOption.objects.get_or_create(
            attribute=attr, value=value,
            defaults={'label': label, 'sort_order': sort_order},
        )

    def seed_injury(self):
        t = self._type(
            'Injury', 'injury',
            'Leave taken due to a physical injury, whether work-related or not.',
            '#EF4444',
        )
        self._attr(t, 'injury_type', 'Injury type', 'select', 1, required=True,
                   help_text='Where did the injury occur?',
                   options=[
                       ('Work related', 'work_related'),
                       ('Home', 'home'),
                       ('Sports', 'sports'),
                       ('Other', 'other'),
                   ])
        self._attr(t, 'injury_occurred_at', 'Date of injury', 'date', 2, required=True)
        self._attr(t, 'body_part', 'Body part affected', 'text', 3, required=True,
                   help_text='e.g. Right wrist, left ankle')
        self._attr(t, 'severity', 'Severity', 'select', 4, required=True,
                   options=[
                       ('Minor', 'minor'),
                       ('Moderate', 'moderate'),
                       ('Severe', 'severe'),
                   ])
        self._attr(
            t, 'medical_certificate', 'Medical certificate',
            'file', 5, required=True,
            rules={'max_size_mb': 10},
        )
        self._attr(
            t, 'doctor_notes', 'Doctor notes', 'richtext', 6, required=False,
            help_text='Recovery plan, restrictions, or notes from the doctor.',
        )
        self._attr(
            t, 'workplace_accident_report', 'Workplace accident report',
            'boolean', 7, required=False, group='Workplace accident',
            help_text='Was an accident report filed? (only if work-related)',
            condition={'depends_on': 'injury_type', 'operator': 'equals', 'value': 'work_related'},
        )
        self._attr(
            t, 'report_number', 'Accident report number', 'text', 8,
            required=False, group='Workplace accident',
            condition={'depends_on': 'workplace_accident_report', 'operator': 'equals', 'value': 'true'},
        )

    def seed_maternity(self):
        t = self._type(
            'Maternity', 'maternity',
            'Leave taken around the birth or adoption of a child.',
            '#EC4899',
        )
        self._attr(t, 'due_date', 'Expected/actual due date', 'date', 1, required=True)
        self._attr(t, 'baby_born_at', 'Birth date', 'date', 2, required=False,
                   help_text='Fill in once the baby arrives.')
        self._attr(t, 'doctor_clearance', 'Doctor clearance letter', 'file', 3, required=True,
                   help_text='Upload the medical clearance.')
        self._attr(t, 'recovery_notes', 'Recovery notes', 'richtext', 4, required=False)

    def seed_paternity(self):
        t = self._type(
            'Paternity', 'paternity',
            'Leave taken for the birth/adoption of a child by a parent.',
            '#8B5CF6',
        )
        self._attr(t, 'birth_date', 'Birth date', 'date', 1, required=True)
        self._attr(t, 'relationship', 'Relationship to child', 'select', 2, required=True,
                   options=[
                       ('Biological parent', 'biological'),
                       ('Adoptive parent', 'adoptive'),
                   ])
        self._attr(t, 'bonding_notes', 'Bonding notes', 'textarea', 3, required=False)

    def seed_bereavement(self):
        t = self._type(
            'Death in the Family', 'death_in_family',
            'Leave taken following the death of a close family member.',
            '#64748B',
        )
        self._attr(t, 'deceased_name', 'Name of deceased', 'text', 1, required=True)
        self._attr(t, 'relationship', 'Relationship', 'select', 2, required=True,
                   options=[
                       ('Spouse/Partner', 'spouse'),
                       ('Parent', 'parent'),
                       ('Child', 'child'),
                       ('Sibling', 'sibling'),
                       ('Grandparent', 'grandparent'),
                       ('Other relative', 'other'),
                   ])
        self._attr(t, 'funeral_date', 'Funeral date', 'date', 3, required=True)
        self._attr(t, 'obituary', 'Obituary / memorial link', 'text', 4, required=False,
                   help_text='Link to obituary or memorial page.')
        self._attr(t, 'support_notes', 'Support notes', 'textarea', 5, required=False,
                   help_text='Anything the team should know to support this person.')
        self._attr(t, 'condolence_card', 'Condolence card', 'boolean', 6, required=False,
                   help_text='Send a company condolence card?')

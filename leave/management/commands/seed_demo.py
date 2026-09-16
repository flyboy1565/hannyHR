from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from employees.models import Employee
from leave.models import LeaveAttrOption, LeaveAttribute, LeaveType


class Command(BaseCommand):
    help = 'Seed demo leave types, attributes, and sample employees.'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='hr').exists():
            User.objects.create_superuser('hr', 'hr@example.com', 'hannyhr123')

        employees = [
            {
                'employee_id': 'EMP-1001', 'first_name': 'Alice', 'last_name': 'Moyo',
                'department': 'Engineering', 'job_title': 'Backend Engineer',
            },
            {
                'employee_id': 'EMP-1002', 'first_name': 'Ben', 'last_name': 'Kariuki',
                'department': 'Design', 'job_title': 'Product Designer',
            },
            {
                'employee_id': 'EMP-1003', 'first_name': 'Clara', 'last_name': 'Okafor',
                'department': 'Finance', 'job_title': 'Accountant',
            },
            {
                'employee_id': 'EMP-1004', 'first_name': 'David', 'last_name': 'Zulu',
                'department': 'Engineering', 'job_title': 'Frontend Engineer',
            },
        ]
        for data in employees:
            Employee.objects.get_or_create(employee_id=data['employee_id'], defaults=data)

        self.seed_injury()
        self.seed_maternity()
        self.seed_paternity()
        self.seed_bereavement()
        self.stdout.write(self.style.SUCCESS('Demo data seeded.'))

    def _type(self, name, slug, description, color):
        obj, _ = LeaveType.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'description': description,
                'color': color,
            },
        )
        # Refresh the display name if it changed on a rerun.
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
        # Clear existing options so reruns converge on the seeded set.
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
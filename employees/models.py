from django.db import models


class Employee(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]

    employee_id = models.CharField('Employee ID', max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=100, blank=True)
    job_title = models.CharField('Job Title', max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name_plural = 'Employees'

    def __str__(self):
        return f'{self.employee_id} — {self.full_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
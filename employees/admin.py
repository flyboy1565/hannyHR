from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'full_name', 'department', 'job_title', 'status', 'hire_date')
    list_filter = ('status', 'department')
    search_fields = ('employee_id', 'first_name', 'last_name', 'email')
    raw_id_fields = ('user',)
    fieldsets = (
        (None, {'fields': ('employee_id', 'first_name', 'last_name', 'email')}),
        ('User Account', {'fields': ('user',), 'classes': ('collapse',)}),
        ('Work', {'fields': ('department', 'job_title', 'hire_date', 'status')}),
    )
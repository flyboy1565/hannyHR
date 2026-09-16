from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from employees.models import Employee

from .forms import (
    LeaveDynamicForm,
    save_dynamic_values,
    values_for_request,
)
from .models import LeaveRequest, LeaveType


class LeaveTypeListView(LoginRequiredMixin, View):
    def get(self, request):
        leave_types = LeaveType.objects.filter(is_active=True).annotate(
            request_count=models.Count('requests')
        )
        recent = LeaveRequest.objects.select_related(
            'employee', 'leave_type'
        )[:10]
        return render(request, 'leave/leave_type_list.html', {
            'leave_types': leave_types,
            'recent': recent,
        })


class LeaveRequestListView(LoginRequiredMixin, View):
    def get(self, request):
        requests = LeaveRequest.objects.select_related(
            'employee', 'leave_type'
        ).prefetch_related('attribute_values__attribute')
        leave_type_slug = request.GET.get('leave_type')
        employee_id = request.GET.get('employee_id')
        if leave_type_slug:
            requests = requests.filter(leave_type__slug=leave_type_slug)
        if employee_id:
            requests = requests.filter(employee_id=employee_id)
        return render(request, 'leave/leave_request_list.html', {
            'requests': requests,
            'leave_types': LeaveType.objects.filter(is_active=True),
            'employees': Employee.objects.filter(status='active').order_by('last_name'),
            'filters': {'leave_type': leave_type_slug or '', 'employee_id': employee_id or ''},
        })


class LeaveRequestCreateView(LoginRequiredMixin, View):
    """Step 1: choose employee + leave type. Step 2: fill dynamic form."""

    def _selection_context(self):
        return {
            'employees': Employee.objects.filter(status='active').order_by('last_name'),
            'leave_types': LeaveType.objects.filter(is_active=True).prefetch_related('attributes'),
        }

    def get(self, request):
        employee_pk = request.GET.get('employee')
        type_pk = request.GET.get('type')
        if not (employee_pk and type_pk):
            return render(
                request, 'leave/leave_type_select.html', self._selection_context()
            )
        employee = get_object_or_404(Employee, pk=employee_pk)
        leave_type = get_object_or_404(LeaveType, pk=type_pk)
        attributes = leave_type.attributes.filter(is_active=True).prefetch_related('options')
        form = LeaveDynamicForm(attributes=attributes)
        form.initial['employee'] = employee.pk
        form.initial['leave_type'] = leave_type.pk
        context = self._selection_context()
        context.update({
            'employee': employee,
            'leave_type': leave_type,
            'form': form,
            'attribute_groups': group_attributes(form),
        })
        return render(request, 'leave/leave_request_form.html', context)

    def post(self, request):
        employee_pk = request.POST.get('employee')
        type_pk = request.POST.get('leave_type')
        employee = get_object_or_404(Employee, pk=employee_pk)
        leave_type = get_object_or_404(LeaveType, pk=type_pk)
        attributes = leave_type.attributes.filter(is_active=True).prefetch_related('options')

        form = LeaveDynamicForm(
            request.POST, request.FILES, attributes=attributes
        )
        if form.is_valid():
            leave_request = LeaveRequest.objects.create(
                employee=employee,
                leave_type=leave_type,
                summary=form.cleaned_data.get('summary', ''),
                start_date=form.cleaned_data.get('start_date'),
                end_date=form.cleaned_data.get('end_date'),
                created_by=request.user,
            )
            save_dynamic_values(leave_request, form)
            messages.success(request, 'Leave documented successfully.')
            return redirect('leave:leave_detail', pk=leave_request.pk)

        context = self._selection_context()
        context.update({
            'employee': employee,
            'leave_type': leave_type,
            'form': form,
            'attribute_groups': group_attributes(form),
        })
        return render(request, 'leave/leave_request_form.html', context)


class LeaveRequestEditView(LoginRequiredMixin, View):
    def get(self, request, pk):
        leave_request = get_object_or_404(
            LeaveRequest.objects.select_related('employee', 'leave_type'), pk=pk
        )
        attributes = list(
            leave_request.leave_type.attributes.filter(is_active=True)
            .prefetch_related('options')
        )
        existing = values_for_request(leave_request)
        form = LeaveDynamicForm(attributes=attributes, existing_values=existing)
        form.initial['employee'] = leave_request.employee_id
        form.initial['leave_type'] = leave_request.leave_type_id
        return render(request, 'leave/leave_request_form.html', {
            'employee': leave_request.employee,
            'leave_type': leave_request.leave_type,
            'form': form,
            'attribute_groups': group_attributes(form),
            'editing': leave_request,
        })

    def post(self, request, pk):
        leave_request = get_object_or_404(
            LeaveRequest.objects.select_related('employee', 'leave_type'), pk=pk
        )
        attributes = list(
            leave_request.leave_type.attributes.filter(is_active=True)
            .prefetch_related('options')
        )
        form = LeaveDynamicForm(
            request.POST, request.FILES, attributes=attributes,
            existing_values=values_for_request(leave_request),
        )
        if form.is_valid():
            leave_request.summary = form.cleaned_data.get('summary', '')
            leave_request.start_date = form.cleaned_data.get('start_date')
            leave_request.end_date = form.cleaned_data.get('end_date')
            leave_request.save()
            save_dynamic_values(leave_request, form)
            messages.success(request, 'Leave documentation updated.')
            return redirect('leave:leave_detail', pk=leave_request.pk)
        return render(request, 'leave/leave_request_form.html', {
            'employee': leave_request.employee,
            'leave_type': leave_request.leave_type,
            'form': form,
            'attribute_groups': group_attributes(form),
            'editing': leave_request,
        })


class LeaveRequestDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        leave_request = get_object_or_404(
            LeaveRequest.objects.select_related('employee', 'leave_type', 'created_by')
            .prefetch_related('attribute_values__attribute__options'),
            pk=pk,
        )
        values = [
            v for v in leave_request.attribute_values.all()
            if v.attribute.is_active or v.display_value
        ]
        values.sort(key=lambda v: (v.attribute.group or '', v.attribute.sort_order))
        return render(request, 'leave/leave_request_detail.html', {
            'request_obj': leave_request,
            'values': values,
        })


def group_attributes(form):
    """Split the form's fields into ordered groups for rendering."""
    grouped = []
    current = []
    current_group = '__ungrouped__'

    def flush():
        nonlocal current_group
        if current:
            grouped.append((current_group, list(current)))
            current.clear()

    for attribute in form.attributes:
        if attribute.group != current_group:
            flush()
            current_group = attribute.group or '__ungrouped__'
        current.append((attribute, form[attribute.name]))
    flush()
    return grouped
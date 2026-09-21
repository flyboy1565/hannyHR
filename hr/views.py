from django.contrib.auth.views import LoginView, LogoutView

from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from employees.models import Employee
from leave.models import LeaveAttribute, LeaveRequest, LeaveType

from .forms import (
    EmployeeForm,
    HRAuthenticationForm,
    LeaveAttrOptionFormSet,
    LeaveAttributeForm,
    LeaveTypeForm,
)
from .mixins import HRConsoleMixin, HRPortalMixin


class HRDashboardView(HRConsoleMixin, TemplateView):
    template_name = 'hr/hr_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'employee_count': Employee.objects.count(),
            'active_employee_count': Employee.objects.filter(status='active').count(),
            'leave_type_count': LeaveType.objects.count(),
            'attribute_count': LeaveAttribute.objects.count(),
            'request_count': LeaveRequest.objects.count(),
            'recent_requests': LeaveRequest.objects.select_related(
                'employee', 'leave_type'
            )[:5],
        })
        return context


# --------------------------------------------------------------------------
# Employees
# --------------------------------------------------------------------------

class EmployeeListView(HRConsoleMixin, ListView):
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 25

    def get_queryset(self):
        qs = Employee.objects.all().order_by('last_name', 'first_name')
        query = self.request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(
                Q(employee_id__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(department__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class EmployeeCreateView(HRConsoleMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')

    def form_valid(self, form):
        messages.success(self.request, 'Employee created.')
        return super().form_valid(form)


class EmployeeUpdateView(HRConsoleMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee_list')

    def form_valid(self, form):
        messages.success(self.request, 'Employee updated.')
        return super().form_valid(form)


class EmployeeDeleteView(HRConsoleMixin, DeleteView):
    model = Employee
    template_name = 'hr/employee_confirm_delete.html'
    success_url = reverse_lazy('hr:employee_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, 'Employee deleted.')
            return response
        except ProtectedError:
            messages.error(
                self.request,
                'Cannot delete: this employee has leave records. '
                'Remove their leave records first.',
            )
            return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Could not delete this employee.')
        return redirect(self.success_url)


# --------------------------------------------------------------------------
# Leave types
# --------------------------------------------------------------------------

class LeaveTypeListView(HRConsoleMixin, ListView):
    model = LeaveType
    template_name = 'hr/leavetype_list.html'
    context_object_name = 'leave_types'

    def get_queryset(self):
        return LeaveType.objects.annotate(
            attribute_count=Count('attributes'),
            request_count=Count('requests'),
        ).order_by('name')


class LeaveTypeCreateView(HRConsoleMixin, CreateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'hr/leavetype_form.html'
    success_url = reverse_lazy('hr:leavetype_list')

    def get_success_url(self):
        return reverse_lazy('hr:leavetype_detail', args=[self.object.pk])

    def form_valid(self, form):
        messages.success(
            self.request,
            'Leave type created. Now add its documentation items.',
        )
        return super().form_valid(form)


class LeaveTypeUpdateView(HRConsoleMixin, UpdateView):
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'hr/leavetype_form.html'
    success_url = reverse_lazy('hr:leavetype_list')

    def form_valid(self, form):
        messages.success(self.request, 'Leave type updated.')
        return super().form_valid(form)


class LeaveTypeDetailView(HRConsoleMixin, TemplateView):
    template_name = 'hr/leavetype_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leave_type = get_object_or_404(
            LeaveType.objects.prefetch_related('attributes__options'),
            pk=self.kwargs['pk'],
        )
        context['leave_type'] = leave_type
        context['attributes'] = leave_type.attributes.all().order_by(
            'sort_order', 'id'
        ) or []
        return context


# --------------------------------------------------------------------------
# Attributes
# --------------------------------------------------------------------------

def _attribute_edit(request, leave_type, attribute=None):
    """Create or edit a LeaveAttribute plus its selectable options."""
    is_create = attribute is None
    attribute = attribute or LeaveAttribute(leave_type=leave_type)
    form = LeaveAttributeForm(
        request.POST or None, instance=attribute, leave_type=leave_type
    )
    option_formset = LeaveAttrOptionFormSet(request.POST or None, instance=attribute)

    if request.method == 'POST' and form.is_valid():
        saved = form.save(commit=False)
        saved.leave_type = leave_type
        saved.save()

        option_formset = LeaveAttrOptionFormSet(request.POST, instance=saved)
        if option_formset.is_valid():
            option_formset.save()
            messages.success(request, 'Attribute saved.')
            return redirect('hr:leavetype_detail', pk=leave_type.pk)

        # Options failed: roll back a create so nothing is left orphaned.
        if is_create:
            saved.delete()
            form = LeaveAttributeForm(
                request.POST, instance=LeaveAttribute(leave_type=leave_type),
                leave_type=leave_type,
            )
        else:
            form = LeaveAttributeForm(request.POST, instance=saved, leave_type=leave_type)

    return render(request, 'hr/attribute_form.html', {
        'form': form,
        'option_formset': option_formset,
        'leave_type': leave_type,
        'attribute': attribute,
    })


def attribute_create(request, leave_type_pk):
    leave_type = get_object_or_404(LeaveType, pk=leave_type_pk)
    return _attribute_edit(request, leave_type)


def attribute_edit(request, leave_type_pk, attribute_pk):
    leave_type = get_object_or_404(LeaveType, pk=leave_type_pk)
    attribute = get_object_or_404(
        LeaveAttribute, pk=attribute_pk, leave_type=leave_type
    )
    return _attribute_edit(request, leave_type, attribute)


def attribute_delete(request, leave_type_pk, attribute_pk):
    leave_type = get_object_or_404(LeaveType, pk=leave_type_pk)
    attribute = get_object_or_404(
        LeaveAttribute, pk=attribute_pk, leave_type=leave_type
    )
    if request.method == 'POST':
        attribute.options.all().delete()
        attribute.delete()
        messages.success(request, f'Attribute "{attribute.label}" deleted.')
        return redirect('hr:leavetype_detail', pk=leave_type.pk)
    return render(request, 'hr/attribute_confirm_delete.html', {
        'leave_type': leave_type,
        'attribute': attribute,
    })


class HRLoginView(LoginView):
    """Purpose-built HR sign-in at /manage/login/.

    Authenticates through :class:`HRAuthenticationForm` so only accounts that
    can actually operate the console (superuser or ``can_manage_hr``) get in.
    A successful login lands on the HR dashboard (or the ``?next=`` target),
    never on Django admin. Already-signed-in users are bounced straight to the
    dashboard.
    """

    template_name = 'hr/login.html'
    authentication_form = HRAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        url = super().get_success_url()
        if url:
            return url
        return reverse_lazy('hr:dashboard')


class HRLogoutView(LogoutView):
    """End the HR session and return to the (reusable) HR sign-in page."""

    next_page = reverse_lazy('hr:login')


# --------------------------------------------------------------------------
# Audit Log
# --------------------------------------------------------------------------

class AuditLogView(HRConsoleMixin, ListView):
    template_name = 'hr/audit_log.html'
    context_object_name = 'log_entries'
    paginate_by = 50

    def get_queryset(self):
        from auditlog.models import LogEntry

        qs = LogEntry.objects.select_related('actor').order_by('-timestamp')

        model = self.request.GET.get('model', '').strip()
        actor_id = self.request.GET.get('actor_id', '').strip()
        action = self.request.GET.get('action', '').strip()

        if model:
            qs = qs.filter(content_type__model=model)
        if actor_id:
            qs = qs.filter(actor_id=actor_id)
        if action:
            qs = qs.filter(action=action)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model

        User = get_user_model()
        context['users'] = User.objects.filter(
            id__in=self.get_queryset().values_list('actor_id', flat=True).distinct()[:50]
        )
        context['filters'] = {
            'model': self.request.GET.get('model', ''),
            'actor_id': self.request.GET.get('actor_id', ''),
            'action': self.request.GET.get('action', ''),
        }
        context['model_choices'] = [
            ('employee', 'Employee'),
            ('leavetype', 'Leave Type'),
            ('leaverequest', 'Leave Request'),
            ('leaveattributevalue', 'Leave Attribute Value'),
        ]
        context['action_choices'] = [
            ('0', 'Create'),
            ('1', 'Update'),
            ('2', 'Delete'),
        ]
        return context


# --------------------------------------------------------------------------
# Team Member Portal
# --------------------------------------------------------------------------

class TeamMemberPortalView(HRPortalMixin, TemplateView):
    template_name = 'hr/team_portal.html'

    def get_context_data(self, **kwargs):
        import datetime
        from django.db.models import Sum
        from django.utils import timezone

        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()
        year_start = datetime.date(today.year, 1, 1)
        year_end = datetime.date(today.year, 12, 31)

        employee = getattr(user, 'employee_profile', None)

        if employee is None:
            context['no_employee'] = True
            return context

        leave_requests = (
            LeaveRequest.objects.filter(
                employee=employee,
                start_date__lte=year_end,
                end_date__gte=year_start,
            )
            .select_related('leave_type')
            .order_by('-start_date')
        )

        total_days = 0
        breakdown = {}

        for lr in leave_requests:
            start = max(lr.start_date, year_start)
            end = min(lr.end_date, year_end)
            days = (end - start).days + 1
            if days > 0:
                total_days += days
                lt_name = lr.leave_type.name
                lt_color = lr.leave_type.color
                if lt_name not in breakdown:
                    breakdown[lt_name] = {'name': lt_name, 'color': lt_color, 'days': 0}
                breakdown[lt_name]['days'] += days

        context.update({
            'employee': employee,
            'year': today.year,
            'leave_requests': leave_requests,
            'total_days': total_days,
            'breakdown': sorted(breakdown.values(), key=lambda x: -x['days']),
        })
        return context

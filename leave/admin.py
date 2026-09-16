import json

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    LeaveAttrOption,
    LeaveAttribute,
    LeaveAttributeValue,
    LeaveRequest,
    LeaveType,
)


class LeaveAttrOptionInline(admin.TabularInline):
    model = LeaveAttrOption
    extra = 1


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_badge', 'is_active', 'attribute_count', 'request_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='')
    def color_badge(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:4px;background:{}"></span>',
            obj.color,
        )

    @admin.display(description='Attributes')
    def attribute_count(self, obj):
        return obj.attributes.count()

    @admin.display(description='Requests')
    def request_count(self, obj):
        return obj.requests.count()


@admin.register(LeaveAttribute)
class LeaveAttributeAdmin(admin.ModelAdmin):
    list_display = (
        'label', 'leave_type', 'field_type_badge', 'required', 'sort_order',
        'has_condition',
    )
    list_filter = ('leave_type', 'field_type', 'required', 'is_active')
    list_editable = ('required', 'sort_order')
    search_fields = ('label', 'name')
    inlines = [LeaveAttrOptionInline]
    fieldsets = (
        (None, {'fields': ('leave_type', 'name', 'label')}),
        ('Behaviour', {'fields': ('field_type', 'required', 'sort_order')}),
        ('Form rendering', {'fields': ('help_text', 'placeholder', 'default_value', 'group')}),
        ('Validation', {'fields': ('validation_rules',)}),
        ('Conditional display', {'fields': ('condition',), 'classes': ('collapse',)}),
        ('Status', {'fields': ('is_active',)}),
    )

    @admin.display(description='Type')
    def field_type_badge(self, obj):
        return obj.get_field_type_display()

    @admin.display(description='Conditional')
    def has_condition(self, obj):
        if obj.has_conditional:
            cond = obj.condition
            return format_html(
                '<span style="color:#b45309">{}</span>',
                f"{cond.get('depends_on')} {cond.get('operator')} {cond.get('value')}",
            )
        return '—'


class LeaveAttributeValueInline(admin.TabularInline):
    model = LeaveAttributeValue
    extra = 0
    readonly_fields = ('attribute_name', 'value_text_preview', 'value_file_preview')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Attribute')
    def attribute_name(self, obj):
        if obj.attribute_id:
            return obj.attribute.label
        return '—'

    @admin.display(description='Value')
    def value_text_preview(self, obj):
        text = obj.value_text
        max_len = 80
        if len(text) > max_len:
            text = text[:max_len] + '…'
        return format_html('<pre style="margin:0">{}</pre>', text)

    @admin.display(description='File')
    def value_file_preview(self, obj):
        if not obj.value_file:
            return '—'
        return format_html('<a href="{}" target="_blank">Download</a>',
                           obj.value_file.url)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        'employee', 'leave_type', 'summary', 'start_date', 'end_date',
        'status', 'created_by', 'created_at',
    )
    list_filter = ('leave_type', 'status')
    search_fields = ('employee__first_name', 'employee__last_name', 'summary')
    date_hierarchy = 'start_date'
    inlines = [LeaveAttributeValueInline]
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('employee', 'leave_type', 'summary', 'status')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Audit', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
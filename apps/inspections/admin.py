# apps/inspections/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    InspectionCategory, 
    InspectionQuestion, 
    InspectionTemplate, 
    TemplateQuestion,
    InspectionSchedule
)


@admin.register(InspectionCategory)
class InspectionCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'category_code', 
        'category_name', 
        'display_order', 
        'questions_count',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['category_name', 'category_code', 'description']
    ordering = ['display_order', 'category_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category_name', 'category_code', 'description', 'icon')
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def questions_count(self, obj):
        count = obj.get_active_questions_count()
        return format_html(
            '<span style="color: #0066cc; font-weight: bold;">{}</span>',
            count
        )
    questions_count.short_description = 'Active Questions'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class TemplateQuestionInline(admin.TabularInline):
    model = TemplateQuestion
    extra = 1
    fields = ['question', 'is_mandatory', 'display_order', 'section_name']
    autocomplete_fields = ['question']
    ordering = ['display_order']


@admin.register(InspectionQuestion)
class InspectionQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'question_code',
        'category',
        'question_preview',
        'question_type',
        'is_critical',
        'is_remarks_mandatory',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'category',
        'question_type',
        'is_critical',
        'is_remarks_mandatory',
        'is_photo_required',
        'auto_generate_finding',
        'is_active',
        'created_at'
    ]
    search_fields = [
        'question_code',
        'question_text',
        'reference_standard',
        'guidance_notes'
    ]
    ordering = ['category', 'display_order', 'question_code']
    readonly_fields = ['question_code', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'category',
                'question_code',
                'question_text',
                'question_type'
            )
        }),
        ('Configuration', {
            'fields': (
                'is_remarks_mandatory',
                'is_photo_required',
                'is_critical',
                'auto_generate_finding',
                'weightage',
                'display_order'
            )
        }),
        ('Reference & Guidance', {
            'fields': ('reference_standard', 'guidance_notes'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        preview = obj.question_text[:60] + '...' if len(obj.question_text) > 60 else obj.question_text
        color = '#dc3545' if obj.is_critical else '#333'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            preview
        )
    question_preview.short_description = 'Question'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['make_active', 'make_inactive', 'mark_as_critical']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} questions marked as active.')
    make_active.short_description = "Mark selected questions as active"
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} questions marked as inactive.')
    make_inactive.short_description = "Mark selected questions as inactive"
    
    def mark_as_critical(self, request, queryset):
        updated = queryset.update(is_critical=True)
        self.message_user(request, f'{updated} questions marked as critical.')
    mark_as_critical.short_description = "Mark as critical questions"


@admin.register(InspectionTemplate)
class InspectionTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'template_code',
        'template_name',
        'inspection_type',
        'questions_count',
        'requires_approval',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'inspection_type',
        'requires_approval',
        'is_active',
        'created_at',
        'applicable_plants'
    ]
    search_fields = ['template_name', 'template_code', 'description']
    filter_horizontal = ['applicable_plants', 'applicable_departments']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TemplateQuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'template_name',
                'template_code',
                'inspection_type',
                'description'
            )
        }),
        ('Applicability', {
            'fields': ('applicable_plants', 'applicable_departments')
        }),
        ('Configuration', {
            'fields': (
                'requires_approval',
                'min_compliance_score',
                'is_active'
            )
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def questions_count(self, obj):
        count = obj.get_total_questions()
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    questions_count.short_description = 'Total Questions'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InspectionSchedule)
class InspectionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'schedule_code',
        'template',
        'assigned_to',
        'plant',
        'scheduled_date',
        'due_date',
        'status_badge',
        'is_overdue'
    ]
    list_filter = [
        'status',
        'plant',
        'scheduled_date',
        'due_date',
        'created_at'
    ]
    search_fields = [
        'schedule_code',
        'assigned_to__first_name',
        'assigned_to__last_name',
        'assigned_to__employee_id'
    ]
    readonly_fields = [
        'schedule_code',
        'started_at',
        'completed_at',
        'reminder_sent_at',
        'created_at',
        'updated_at'
    ]
    autocomplete_fields = ['assigned_to', 'assigned_by']
    
    fieldsets = (
        ('Schedule Information', {
            'fields': (
                'schedule_code',
                'template',
                'status'
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_to',
                'assigned_by',
                'assignment_notes'
            )
        }),
        ('Location Details', {
            'fields': (
                'plant',
                'zone',
                'location',
                'sublocation',
                'department'
            )
        }),
        ('Timing', {
            'fields': (
                'scheduled_date',
                'due_date',
                'started_at',
                'completed_at'
            )
        }),
        ('Notifications', {
            'fields': (
                'reminder_sent',
                'reminder_sent_at'
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'SCHEDULED': '#007bff',
            'IN_PROGRESS': '#ffc107',
            'COMPLETED': '#28a745',
            'OVERDUE': '#dc3545',
            'CANCELLED': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def is_overdue(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ Yes</span>'
            )
        return format_html(
            '<span style="color: #28a745;">✓ No</span>'
        )
    is_overdue.short_description = 'Overdue'
    
    actions = ['send_reminders', 'mark_as_completed', 'cancel_schedules']
    
    def send_reminders(self, request, queryset):
        # Implement reminder sending logic
        count = queryset.filter(status='SCHEDULED').count()
        self.message_user(request, f'Reminders sent for {count} scheduled inspections.')
    send_reminders.short_description = "Send reminder notifications"
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['SCHEDULED', 'IN_PROGRESS']).update(
            status='COMPLETED',
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} inspections marked as completed.')
    mark_as_completed.short_description = "Mark as completed"
    
    def cancel_schedules(self, request, queryset):
        updated = queryset.exclude(status='COMPLETED').update(status='CANCELLED')
        self.message_user(request, f'{updated} inspections cancelled.')
    cancel_schedules.short_description = "Cancel selected schedules"
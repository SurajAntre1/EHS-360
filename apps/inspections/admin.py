# apps/inspections/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Q
from .models import (
    InspectionTemplate, InspectionCategory, InspectionPoint,
    InspectionSchedule, Inspection, InspectionResponse,
    InspectionFinding, InspectionAttachment
)


class InspectionCategoryInline(admin.TabularInline):
    model = InspectionCategory
    extra = 1
    fields = ['category_name', 'sequence_order', 'is_active']
    ordering = ['sequence_order']


class InspectionPointInline(admin.TabularInline):
    model = InspectionPoint
    extra = 1
    fields = ['inspection_point_text', 'sequence_order', 'is_mandatory', 'requires_photo', 'is_active']
    ordering = ['sequence_order']


@admin.register(InspectionTemplate)
class InspectionTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'template_name', 'template_code', 'frequency', 
        'category_count_display', 'total_points_display', 
        'is_active', 'created_at'
    ]
    list_filter = ['frequency', 'is_active', 'created_at']
    search_fields = ['template_name', 'template_code', 'description']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    inlines = [InspectionCategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('template_name', 'template_code', 'description')
        }),
        ('Configuration', {
            'fields': ('frequency', 'document_number', 'is_active')
        }),
        ('System Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_count_display(self, obj):
        count = obj.category_count
        return format_html(
            '<span style="background-color: #17a2b8; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    category_count_display.short_description = 'Categories'
    
    def total_points_display(self, obj):
        count = obj.total_inspection_points
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    total_points_display.short_description = 'Total Points'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InspectionCategory)
class InspectionCategoryAdmin(admin.ModelAdmin):
    list_display = ['category_name', 'template', 'sequence_order', 'point_count_display', 'is_active']
    list_filter = ['template', 'is_active']
    search_fields = ['category_name', 'template__template_name']
    ordering = ['template', 'sequence_order']
    inlines = [InspectionPointInline]
    
    def point_count_display(self, obj):
        count = obj.inspection_point_count
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 3px 10px; border-radius: 3px;">{}</span>',
            count
        )
    point_count_display.short_description = 'Inspection Points'


@admin.register(InspectionPoint)
class InspectionPointAdmin(admin.ModelAdmin):
    list_display = [
        'inspection_point_short', 'category', 'sequence_order',
        'is_mandatory', 'requires_photo', 'is_active'
    ]
    list_filter = ['category__template', 'category', 'is_mandatory', 'requires_photo', 'is_active']
    search_fields = ['inspection_point_text', 'category__category_name']
    ordering = ['category', 'sequence_order']
    
    def inspection_point_short(self, obj):
        return obj.inspection_point_text[:80] + '...' if len(obj.inspection_point_text) > 80 else obj.inspection_point_text
    inspection_point_short.short_description = 'Inspection Point'


@admin.register(InspectionSchedule)
class InspectionScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'template', 'plant', 'assigned_to', 'scheduled_date',
        'due_date', 'status_display', 'days_until_due_display'
    ]
    list_filter = ['status', 'template', 'plant', 'scheduled_date', 'due_date']
    search_fields = ['template__template_name', 'plant__name', 'assigned_to__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        ('Inspection Details', {
            'fields': ('template', 'plant', 'zone', 'location')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assigned_by', 'scheduled_date', 'due_date')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'SCHEDULED': '#6c757d',
            'IN_PROGRESS': '#ffc107',
            'COMPLETED': '#28a745',
            'OVERDUE': '#dc3545',
            'CANCELLED': '#343a40',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def days_until_due_display(self, obj):
        days = obj.days_until_due
        if days < 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Overdue by {} days</span>',
                abs(days)
            )
        elif days == 0:
            return format_html('<span style="color: #ffc107; font-weight: bold;">Due Today</span>')
        else:
            return format_html(
                '<span style="color: #17a2b8;">{} days</span>',
                days
            )
    days_until_due_display.short_description = 'Days Until Due'


class InspectionResponseInline(admin.TabularInline):
    model = InspectionResponse
    extra = 0
    fields = ['inspection_point', 'response', 'remarks']
    readonly_fields = ['inspection_point']
    can_delete = False


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = [
        'inspection_number', 'template', 'plant', 'location',
        'conducted_by', 'inspection_date', 'compliance_display',
        'findings_count_display', 'status_display'
    ]
    list_filter = [
        'status', 'template', 'plant', 'inspection_date',
        'month', 'year'
    ]
    search_fields = [
        'inspection_number', 'template__template_name',
        'plant__name', 'conducted_by__username'
    ]
    readonly_fields = [
        'inspection_number', 'overall_score', 'total_findings',
        'submitted_at', 'reviewed_at', 'approved_at',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'inspection_date'
    inlines = [InspectionResponseInline]
    
    fieldsets = (
        ('Inspection Information', {
            'fields': (
                'inspection_number', 'template', 'inspection_schedule',
                'inspection_date', 'month', 'year'
            )
        }),
        ('Location Details', {
            'fields': ('plant', 'zone', 'location', 'department')
        }),
        ('Conducted By', {
            'fields': ('conducted_by',)
        }),
        ('Status & Scores', {
            'fields': ('status', 'overall_score', 'total_findings')
        }),
        ('Review Information', {
            'fields': (
                'submitted_at', 'reviewed_by', 'reviewed_at', 'review_comments',
                'approved_by', 'approved_at'
            ),
            'classes': ('collapse',)
        }),
        ('Attachments', {
            'fields': ('pdf_report',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def compliance_display(self, obj):
        score = obj.overall_score or 0
        if score >= 90:
            color = '#28a745'
        elif score >= 70:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{:.1f}%</span>',
            color,
            score
        )
    compliance_display.short_description = 'Compliance Score'
    
    def findings_count_display(self, obj):
        count = obj.total_findings
        if count > 0:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
                count
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">0</span>'
        )
    findings_count_display.short_description = 'Findings'
    
    def status_display(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'SUBMITTED': '#17a2b8',
            'UNDER_REVIEW': '#ffc107',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(InspectionResponse)
class InspectionResponseAdmin(admin.ModelAdmin):
    list_display = [
        'inspection', 'category', 'inspection_point_short',
        'response_display', 'has_remarks', 'has_photos'
    ]
    list_filter = ['response', 'inspection__template', 'category']
    search_fields = [
        'inspection__inspection_number',
        'inspection_point__inspection_point_text',
        'remarks'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def inspection_point_short(self, obj):
        text = obj.inspection_point.inspection_point_text
        return text[:50] + '...' if len(text) > 50 else text
    inspection_point_short.short_description = 'Inspection Point'
    
    def response_display(self, obj):
        colors = {
            'YES': '#28a745',
            'NO': '#dc3545',
            'NA': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.response, '#6c757d'),
            obj.response
        )
    response_display.short_description = 'Response'
    
    def has_remarks(self, obj):
        return bool(obj.remarks)
    has_remarks.boolean = True
    has_remarks.short_description = 'Remarks'
    
    def has_photos(self, obj):
        return bool(obj.photo_1 or obj.photo_2 or obj.photo_3)
    has_photos.boolean = True
    has_photos.short_description = 'Photos'


@admin.register(InspectionFinding)
class InspectionFindingAdmin(admin.ModelAdmin):
    list_display = [
        'finding_number', 'inspection', 'category_name',
        'severity_display', 'assigned_to', 'target_date',
        'status_display', 'overdue_indicator'
    ]
    list_filter = [
        'status', 'severity', 'inspection__plant',
        'target_date', 'closure_date'
    ]
    search_fields = [
        'finding_number', 'inspection__inspection_number',
        'inspection_point_text', 'remarks'
    ]
    readonly_fields = [
        'finding_number', 'inspection_response', 'target_date',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Finding Information', {
            'fields': (
                'finding_number', 'inspection', 'inspection_response',
                'inspection_point_text', 'category_name', 'remarks'
            )
        }),
        ('Classification', {
            'fields': ('severity', 'status')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assigned_by', 'target_date')
        }),
        ('Action Taken', {
            'fields': (
                'action_taken_description',
                'action_taken_photo_1', 'action_taken_photo_2', 'action_taken_photo_3'
            ),
            'classes': ('collapse',)
        }),
        ('Closure', {
            'fields': ('closure_date', 'closure_remarks', 'closed_by'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def severity_display(self, obj):
        colors = {
            'CRITICAL': '#dc3545',
            'HIGH': '#fd7e14',
            'MEDIUM': '#ffc107',
            'LOW': '#17a2b8',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display()
        )
    severity_display.short_description = 'Severity'
    
    def status_display(self, obj):
        colors = {
            'OPEN': '#dc3545',
            'IN_PROGRESS': '#ffc107',
            'UNDER_REVIEW': '#17a2b8',
            'CLOSED': '#28a745',
            'REJECTED': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def overdue_indicator(self, obj):
        if obj.is_overdue:
            days = abs(obj.days_until_due)
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ {} days overdue</span>',
                days
            )
        return format_html('<span style="color: #28a745;">✓ On track</span>')
    overdue_indicator.short_description = 'Overdue Status'


@admin.register(InspectionAttachment)
class InspectionAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 'inspection', 'finding',
        'file_type', 'file_size_display', 'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'inspection__inspection_number', 'finding__finding_number']
    readonly_fields = ['file_size', 'uploaded_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            size_kb = obj.file_size / 1024
            if size_kb < 1024:
                return f"{size_kb:.2f} KB"
            else:
                size_mb = size_kb / 1024
                return f"{size_mb:.2f} MB"
        return "Unknown"
    file_size_display.short_description = 'File Size'



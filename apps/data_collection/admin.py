# apps/data_collection/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .models import *

@admin.register(DataCollectionCategory)
class DataCollectionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'display_order', 'question_count', 
                    'active_question_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Display Settings', {
            'fields': ('icon_class', 'display_order', 'is_active')
        }),
    )
    
    def question_count(self, obj):
        count = obj.question_count
        url = reverse('admin:data_collection_datacollectionquestion_changelist')
        return format_html(
            '<a href="{}?category__id__exact={}">{} questions</a>',
            url, obj.id, count
        )
    question_count.short_description = 'Total Questions'
    
    def active_question_count(self, obj):
        return obj.active_question_count
    active_question_count.short_description = 'Active Questions'


@admin.register(DataCollectionQuestion)
class DataCollectionQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'question_code', 'category', 'field_type', 
                    'is_required', 'unit_of_measurement', 'display_order', 'is_active']
    list_filter = ['category', 'field_type', 'is_required', 'is_active', 
                   'applicable_to_all_plants', 'created_at']
    search_fields = ['question_text', 'question_code', 'help_text']
    ordering = ['category', 'display_order', 'question_text']
    
    filter_horizontal = ['applicable_plants']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'question_text', 'question_code', 'field_type')
        }),
        ('Field Configuration', {
            'fields': ('help_text', 'placeholder', 'unit_of_measurement', 'options_json')
        }),
        ('Validation Rules', {
            'fields': ('is_required', 'min_value', 'max_value', 'min_length', 'max_length'),
            'classes': ('collapse',)
        }),
        ('Display & Assignment', {
            'fields': ('display_order', 'show_on_summary', 
                      'applicable_to_all_plants', 'applicable_plants')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        obj.clean()
        super().save_model(request, obj, form, change)


@admin.register(DataCollectionPeriod)
class DataCollectionPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'month', 'start_date', 'end_date', 
                    'submission_deadline', 'status_badge', 'collection_count', 
                    'days_remaining_display']
    list_filter = ['status', 'year', 'month']
    search_fields = ['name', 'description']
    ordering = ['-year', '-month']
    
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Period Information', {
            'fields': ('name', 'year', 'month')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'submission_deadline')
        }),
        ('Status & Description', {
            'fields': ('status', 'description')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'ACTIVE': 'green',
            'CLOSED': 'orange',
            'ARCHIVED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def collection_count(self, obj):
        count = obj.collections.count()
        url = reverse('admin:data_collection_monthlydatacollection_changelist')
        return format_html(
            '<a href="{}?period__id__exact={}">{} collections</a>',
            url, obj.id, count
        )
    collection_count.short_description = 'Collections'
    
    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days is None:
            return 'N/A'
        if days < 0:
            return format_html('<span style="color: red;">Overdue by {} days</span>', abs(days))
        elif days == 0:
            return format_html('<span style="color: orange;">Due today</span>')
        elif days <= 3:
            return format_html('<span style="color: orange;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    days_remaining_display.short_description = 'Time Remaining'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class DataCollectionResponseInline(admin.TabularInline):
    model = DataCollectionResponse
    extra = 0
    fields = ['question', 'get_value_display', 'unit_used', 'remarks']
    readonly_fields = ['get_value_display']
    can_delete = False
    
    def get_value_display(self, obj):
        if obj.pk:
            return obj.get_display_value()
        return '-'
    get_value_display.short_description = 'Value'
    
    def has_add_permission(self, request, obj=None):
        return False


class DataCollectionAttachmentInline(admin.TabularInline):
    model = DataCollectionAttachment
    extra = 0
    fields = ['file', 'filename', 'description', 'file_size_display', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['filename', 'file_size_display', 'uploaded_by', 'uploaded_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / 1024:.2f} KB"
        return 'N/A'
    file_size_display.short_description = 'File Size'


class DataCollectionCommentInline(admin.TabularInline):
    model = DataCollectionComment
    extra = 1
    fields = ['comment', 'is_internal', 'commented_by', 'commented_at']
    readonly_fields = ['commented_by', 'commented_at']


@admin.register(MonthlyDataCollection)
class MonthlyDataCollectionAdmin(admin.ModelAdmin):
    list_display = ['period', 'plant', 'location', 'status_badge', 
                    'completion_display', 'reported_by', 'submitted_at', 
                    'approved_at', 'response_count']
    list_filter = ['status', 'period', 'plant', 'submitted_at', 'approved_at']
    search_fields = ['period__name', 'plant__name', 'location__name', 
                     'reported_by__username', 'reported_by__first_name', 
                     'reported_by__last_name']
    ordering = ['-period__year', '-period__month', 'plant', 'location']
    
    readonly_fields = ['reported_by', 'reported_at', 'submitted_by', 'submitted_at',
                       'reviewed_by', 'reviewed_at', 'approved_by', 'approved_at',
                       'completion_display', 'created_at', 'updated_at']
    
    inlines = [DataCollectionResponseInline, DataCollectionAttachmentInline, 
               DataCollectionCommentInline]
    
    fieldsets = (
        ('Period & Location', {
            'fields': ('period', 'plant', 'zone', 'location', 'sublocation', 'department')
        }),
        ('Status', {
            'fields': ('status', 'completion_display')
        }),
        ('Reporting Information', {
            'fields': ('reported_by', 'reported_at', 'remarks')
        }),
        ('Submission Information', {
            'fields': ('submitted_by', 'submitted_at'),
            'classes': ('collapse',)
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_comments'),
            'classes': ('collapse',)
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_at', 'approval_comments'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_selected', 'reject_selected', 'mark_under_review']
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'SUBMITTED': '#007bff',
            'UNDER_REVIEW': '#ffc107',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def completion_display(self, obj):
        percentage = obj.completion_percentage
        color = '#28a745' if percentage == 100 else '#ffc107' if percentage >= 50 else '#dc3545'
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; color: white; '
            'text-align: center; border-radius: 3px; padding: 2px;">{}%</div></div>',
            percentage, color, percentage
        )
    completion_display.short_description = 'Completion'
    
    def response_count(self, obj):
        count = obj.responses.count()
        return format_html('<strong>{}</strong> responses', count)
    response_count.short_description = 'Responses'
    
    def approve_selected(self, request, queryset):
        count = 0
        for collection in queryset:
            if collection.can_approve:
                try:
                    collection.approve(request.user, comments='Approved via admin action')
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error approving {collection}: {str(e)}', 
                                      level='error')
        
        if count > 0:
            self.message_user(request, f'{count} collection(s) approved successfully')
    approve_selected.short_description = 'Approve selected collections'
    
    def reject_selected(self, request, queryset):
        count = 0
        for collection in queryset:
            if collection.can_approve:
                try:
                    collection.reject(request.user, comments='Rejected via admin action')
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error rejecting {collection}: {str(e)}', 
                                      level='error')
        
        if count > 0:
            self.message_user(request, f'{count} collection(s) rejected successfully')
    reject_selected.short_description = 'Reject selected collections'
    
    def mark_under_review(self, request, queryset):
        count = 0
        for collection in queryset.filter(status='SUBMITTED'):
            try:
                collection.review(request.user, comments='Marked for review via admin action')
                count += 1
            except Exception as e:
                self.message_user(request, f'Error reviewing {collection}: {str(e)}', 
                                  level='error')
        
        if count > 0:
            self.message_user(request, f'{count} collection(s) marked under review')
    mark_under_review.short_description = 'Mark as under review'


@admin.register(DataCollectionResponse)
class DataCollectionResponseAdmin(admin.ModelAdmin):
    list_display = ['collection', 'question', 'value_display', 'unit_used', 'updated_at']
    list_filter = ['question__category', 'question__field_type', 'collection__status', 
                   'updated_at']
    search_fields = ['collection__period__name', 'question__question_text', 
                     'question__question_code', 'text_value']
    ordering = ['-updated_at']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Response Information', {
            'fields': ('collection', 'question')
        }),
        ('Value Fields', {
            'fields': ('numeric_value', 'text_value', 'date_value', 
                      'boolean_value', 'selected_option', 'file_value')
        }),
        ('Additional Information', {
            'fields': ('unit_used', 'remarks')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def value_display(self, obj):
        return obj.get_display_value()
    value_display.short_description = 'Value'


@admin.register(DataCollectionAttachment)
class DataCollectionAttachmentAdmin(admin.ModelAdmin):
    list_display = ['collection', 'filename', 'file_size_display', 
                    'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename', 'description', 'collection__period__name']
    ordering = ['-uploaded_at']
    
    readonly_fields = ['filename', 'file_size', 'uploaded_by', 'uploaded_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.2f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return 'N/A'
    file_size_display.short_description = 'File Size'


@admin.register(DataCollectionComment)
class DataCollectionCommentAdmin(admin.ModelAdmin):
    list_display = ['collection', 'comment_preview', 'commented_by', 
                    'is_internal', 'commented_at']
    list_filter = ['is_internal', 'commented_at']
    search_fields = ['comment', 'collection__period__name']
    ordering = ['-commented_at']
    
    readonly_fields = ['commented_by', 'commented_at']
    
    def comment_preview(self, obj):
        return obj.comment[:100] + '...' if len(obj.comment) > 100 else obj.comment
    comment_preview.short_description = 'Comment'


@admin.register(DataCollectionAssignment)
class DataCollectionAssignmentAdmin(admin.ModelAdmin):
    list_display = ['period', 'assigned_to', 'plant', 'location', 
                    'notification_status', 'assigned_by', 'assigned_at']
    list_filter = ['notification_sent', 'reminder_sent', 'period', 'plant', 'assigned_at']
    search_fields = ['assigned_to__username', 'assigned_to__first_name', 
                     'assigned_to__last_name', 'plant__name', 'location__name']
    ordering = ['-assigned_at']
    
    readonly_fields = ['assigned_by', 'assigned_at']
    
    fieldsets = (
        ('Assignment Information', {
            'fields': ('period', 'assigned_to')
        }),
        ('Location', {
            'fields': ('plant', 'zone', 'location', 'sublocation')
        }),
        ('Notification Status', {
            'fields': ('notification_sent', 'reminder_sent')
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at'),
            'classes': ('collapse',)
        }),
    )
    
    def notification_status(self, obj):
        status = []
        if obj.notification_sent:
            status.append('<span style="color: green;">✓ Notified</span>')
        else:
            status.append('<span style="color: red;">✗ Not Notified</span>')
        
        if obj.reminder_sent:
            status.append('<span style="color: green;">✓ Reminded</span>')
        
        return mark_safe(' | '.join(status))
    notification_status.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)
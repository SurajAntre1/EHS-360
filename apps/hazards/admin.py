from django.contrib import admin
from .models import Hazard, HazardPhoto, HazardActionItem


@admin.register(Hazard)
class HazardAdmin(admin.ModelAdmin):
    list_display = [
        'report_number',
        'hazard_category',
        'incident_datetime',
        'hazard_title',
        'plant',
        'severity',
        'status',
        'reported_by',
        'reported_date'
    ]
    list_filter = [
        'hazard_category',
        'severity',
        'status',
        'plant',
        'incident_datetime',
        'reported_date'
    ]
    search_fields = [
        'report_number',
        'hazard_title',
        'hazard_description',
        'reporter_name',
        'reporter_email'
    ]
    readonly_fields = [
        'report_number',
        'reported_date',
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'incident_datetime'
    
    fieldsets = (
        ('Report Information', {
            'fields': (
                'report_number',
                'status',
                'reported_by',
                'reported_date'
            )
        }),
        ('Reporter Information', {
            'fields': (
                'reporter_name',
                'reporter_email',
                'reporter_phone'
            )
        }),
        ('Hazard Details', {
            'fields': (
                'hazard_title',
                'hazard_description',
                'hazard_category',
                'incident_datetime',
                'severity'
            )
        }),
        ('Location Information', {
            'fields': (
                'plant',
                'zone',
                'location',
                'location_details',
                'gps_latitude',
                'gps_longitude'
            )
        }),
        ('Additional Information', {
            'fields': (
                'injury_status',
                'immediate_action',
                'witnesses'
            )
        }),
        ('Assignment & Actions', {
            'fields': (
                'assigned_to',
                'corrective_action_plan',
                'action_deadline',
                'action_completed_date'
            )
        }),
        ('Closure', {
            'fields': (
                'closure_date',
                'closure_remarks'
            )
        }),
        ('System Information', {
            'fields': (
                'report_timestamp',
                'user_agent',
                'report_source',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('plant', 'zone', 'location', 'reported_by', 'assigned_to')


@admin.register(HazardPhoto)
class HazardPhotoAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'hazard',
        'description',
        'uploaded_by',
        'uploaded_at'
    ]
    list_filter = [
        'uploaded_at'
    ]
    search_fields = [
        'hazard__report_number',
        'description'
    ]
    readonly_fields = [
        'uploaded_at'
    ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('hazard', 'uploaded_by')


@admin.register(HazardActionItem)
class HazardActionItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'hazard',
        'action_description_short',
        'responsible_person',
        'target_date',
        'status',
        'completion_date'
    ]
    list_filter = [
        'status',
        'target_date',
        'completion_date'
    ]
    search_fields = [
        'hazard__report_number',
        'action_description'
    ]
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    date_hierarchy = 'target_date'
    
    fieldsets = (
        ('Action Information', {
            'fields': (
                'hazard',
                'action_description',
                'status'
            )
        }),
        ('Assignment', {
            'fields': (
                'responsible_person',
                'target_date'
            )
        }),
        ('Completion', {
            'fields': (
                'completion_date',
                'completion_remarks',
                'verified_by',
                'verification_date'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def action_description_short(self, obj):
        """Return shortened action description"""
        if len(obj.action_description) > 50:
            return obj.action_description[:50] + '...'
        return obj.action_description
    action_description_short.short_description = 'Action Description'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('hazard', 'responsible_person', 'verified_by')
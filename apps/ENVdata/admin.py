from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import (
    UnitCategory,
    Unit,
    EnvironmentalQuestion,
    MonthlyIndicatorData
)


# =========================================================
# UNIT CATEGORY ADMIN
# =========================================================

@admin.register(UnitCategory)
class UnitCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'description_preview',
        'units_count',
        'is_active_badge',
        'created_at',
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_per_page = 25
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def description_preview(self, obj):
        """Show first 50 characters of description"""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = 'Description'
    
    def units_count(self, obj):
        """Count of units in this category"""
        count = obj.units.filter(is_active=True).count()
        return format_html(
            '<span style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">{}</span>',
            count
        )
    units_count.short_description = 'Units'
    
    def is_active_badge(self, obj):
        """Show active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">Active</span>'
            )
        return format_html(
            '<span style="background: #e74c3c; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset with annotations"""
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _units_count=Count('units', filter=Q(units__is_active=True))
        )
        return queryset


# =========================================================
# UNIT ADMIN
# =========================================================

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'category_badge',
        'base_unit',
        'conversion_rate',
        'is_active_badge',
        'created_by',
    ]
    list_filter = ['is_active', 'category', 'created_by']
    search_fields = ['name', 'base_unit', 'category__name']
    list_per_page = 25
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Unit Information', {
            'fields': ('category', 'name', 'base_unit', 'conversion_rate', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )
    
    autocomplete_fields = ['category']
    
    def category_badge(self, obj):
        """Show category as colored badge"""
        return format_html(
            '<span style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">{}</span>',
            obj.category.name
        )
    category_badge.short_description = 'Category'
    
    def is_active_badge(self, obj):
        """Show active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">Active</span>'
            )
        return format_html(
            '<span style="background: #e74c3c; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'


# =========================================================
# ENVIRONMENTAL QUESTION ADMIN
# =========================================================

@admin.register(EnvironmentalQuestion)
class EnvironmentalQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'order',
        'question_preview',
        'category_badge',
        'default_unit_badge',
        'selected_units_display',
        'is_active_badge',
        'created_at',
    ]
    list_filter = ['is_active', 'unit_category', 'created_at']
    search_fields = ['question_text', 'unit_category__name']
    list_per_page = 25
    ordering = ['order', 'id']
    list_editable = ['order']
    
    fieldsets = (
        ('Question Information', {
            'fields': ('question_text', 'order', 'is_active')
        }),
        ('Unit Configuration', {
            'fields': ('unit_category', 'default_unit', 'selected_units')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['selected_units']
    
    def question_preview(self, obj):
        """Show first 80 characters of question"""
        text = obj.question_text
        preview = text[:80] + '...' if len(text) > 80 else text
        return format_html('<strong>{}</strong>', preview)
    question_preview.short_description = 'Question'
    
    def category_badge(self, obj):
        """Show category as colored badge"""
        if obj.unit_category:
            return format_html(
                '<span style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">{}</span>',
                obj.unit_category.name
            )
        return format_html(
            '<span style="background: #95a5a6; color: white; padding: 3px 10px; border-radius: 3px;">Not Set</span>'
        )
    category_badge.short_description = 'Category'
    
    def default_unit_badge(self, obj):
        """Show default unit as badge"""
        if obj.default_unit:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">{}</span>',
                obj.default_unit.name
            )
        return format_html(
            '<span style="background: #95a5a6; color: white; padding: 3px 10px; border-radius: 3px;">Not Set</span>'
        )
    default_unit_badge.short_description = 'Default Unit'
    
    def selected_units_display(self, obj):
        """Show selected units as badges"""
        units = obj.selected_units.all()[:5]  # Show first 5
        if not units:
            return '-'
        
        badges = ''.join([
            f'<span style="background: #f39c12; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-right: 3px;">{unit.name}</span>'
            for unit in units
        ])
        
        count = obj.selected_units.count()
        if count > 5:
            badges += f'<span style="color: #7f8c8d; font-size: 11px;"> +{count - 5} more</span>'
        
        return format_html(badges)
    selected_units_display.short_description = 'Selected Units'
    
    def is_active_badge(self, obj):
        """Show active status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">Active</span>'
            )
        return format_html(
            '<span style="background: #e74c3c; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">Inactive</span>'
        )
    is_active_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'unit_category', 
            'default_unit', 
            'created_by'
        ).prefetch_related('selected_units')
        return queryset


# =========================================================
# MONTHLY INDICATOR DATA ADMIN
# =========================================================

@admin.register(MonthlyIndicatorData)
class MonthlyIndicatorDataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'plant_badge',
        'indicator_preview',
        'month_badge',
        'value_display',
        'unit_badge',
        'created_by',
        'updated_at',
    ]
    list_filter = [
        'plant',
        'month',
        'unit',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'plant__name',
        'indicator',
        'value',
        'unit',
    ]
    list_per_page = 50
    ordering = ['-updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Data Information', {
            'fields': ('plant', 'indicator', 'month', 'value', 'unit')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def plant_badge(self, obj):
        """Show plant as colored badge"""
        return format_html(
            '<span style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">{}</span>',
            obj.plant.name
        )
    plant_badge.short_description = 'Plant'
    
    def indicator_preview(self, obj):
        """Show first 60 characters of indicator"""
        text = obj.indicator
        preview = text[:60] + '...' if len(text) > 60 else text
        return format_html('<strong>{}</strong>', preview)
    indicator_preview.short_description = 'Indicator'
    
    def month_badge(self, obj):
        """Show month as badge"""
        month_colors = {
            'jan': '#e74c3c', 'feb': '#e67e22', 'mar': '#f39c12',
            'apr': '#f1c40f', 'may': '#2ecc71', 'jun': '#1abc9c',
            'jul': '#3498db', 'aug': '#9b59b6', 'sep': '#34495e',
            'oct': '#e67e22', 'nov': '#95a5a6', 'dec': '#7f8c8d',
        }
        color = month_colors.get(obj.month.lower(), '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600; text-transform: uppercase;">{}</span>',
            color,
            obj.month
        )
    month_badge.short_description = 'Month'
    
    def value_display(self, obj):
        """Display value with formatting"""
        try:
            value = float(obj.value)
            if value == 0:
                color = '#e74c3c'
            elif value < 10:
                color = '#f39c12'
            else:
                color = '#27ae60'
            
            formatted_value = f"{value:,.2f}" if value < 1000 else f"{value:,.0f}"
            
            return format_html(
                '<span style="color: {}; font-weight: 700; font-size: 14px;">{}</span>',
                color,
                formatted_value
            )
        except (ValueError, TypeError):
            return format_html(
                '<span style="color: #95a5a6;">{}</span>',
                obj.value
            )
    value_display.short_description = 'Value'
    
    def unit_badge(self, obj):
        """Show unit as badge"""
        return format_html(
            '<span style="background: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: 600;">{}</span>',
            obj.unit
        )
    unit_badge.short_description = 'Unit'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('plant', 'created_by')
        return queryset
    
    # Add actions
    actions = ['export_to_csv']
    
    def export_to_csv(self, request, queryset):
        """Export selected data to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="environmental_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Plant', 'Indicator', 'Month', 'Value', 'Unit', 'Created By', 'Created At'])
        
        for obj in queryset:
            writer.writerow([
                obj.plant.name,
                obj.indicator,
                obj.month,
                obj.value,
                obj.unit,
                obj.created_by.get_full_name() if obj.created_by else '',
                obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    export_to_csv.short_description = "Export selected to CSV"


# =========================================================
# ADMIN SITE CUSTOMIZATION
# =========================================================

# Customize admin site header and title
admin.site.site_header = "EHS-360 Environmental Data Administration"
admin.site.site_title = "Environmental Data Admin"
admin.site.index_title = "Environmental Data Management"
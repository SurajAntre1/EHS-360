from django.contrib import admin
from .models import *


class SubLocationInline(admin.TabularInline):
    model = SubLocation
    extra = 1
    fields = ['name', 'code', 'description', 'is_active']


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'city', 'state', 'contact_person', 'is_active', 'created_at']
    list_filter = ['is_active', 'state', 'city']
    search_fields = ['name', 'code', 'city', 'contact_person']
    ordering = ['name']


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'plant', 'is_active', 'created_at']
    list_filter = ['is_active', 'plant']
    search_fields = ['name', 'code', 'plant__name']
    ordering = ['plant', 'name']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'zone', 'get_plant', 'sublocation_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'zone__plant', 'zone']
    search_fields = ['name', 'code', 'zone__name', 'zone__plant__name']
    ordering = ['zone__plant', 'zone', 'name']
    inlines = [SubLocationInline]  # ADD THIS LINE
    
    def get_plant(self, obj):
        return obj.zone.plant.name
    get_plant.short_description = 'Plant'
    get_plant.admin_order_field = 'zone__plant__name'
    
    def sublocation_count(self, obj):
        return obj.sublocations.count()
    sublocation_count.short_description = 'Sub-Locations'


@admin.register(SubLocation)
class SubLocationAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'location', 'get_zone', 'get_plant', 'is_active', 'created_at']
    list_filter = ['is_active', 'location__zone__plant', 'location__zone']
    search_fields = ['name', 'code', 'location__name', 'location__zone__name', 'location__zone__plant__name']
    ordering = ['location__zone__plant', 'location__zone', 'location', 'name']
    
    def get_zone(self, obj):
        return obj.location.zone.name
    get_zone.short_description = 'Zone'
    get_zone.admin_order_field = 'location__zone__name'
    
    def get_plant(self, obj):
        return obj.location.zone.plant.name
    get_plant.short_description = 'Plant'
    get_plant.admin_order_field = 'location__zone__plant__name'


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'head_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'head_name']
    ordering = ['name']
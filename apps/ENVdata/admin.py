from django.contrib import admin
from .models import UnitCategory, Unit

@admin.register(UnitCategory)
class UnitCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active")
    search_fields = ("name",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "base_unit", "conversion_rate", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)

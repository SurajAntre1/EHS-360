from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UnitCategory(models.Model):
    """
    Category of units like Weight, Volume, Energy, Time, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Unit Category"
        verbose_name_plural = "Unit Categories"

    def __str__(self):
        return self.name


class Unit(models.Model):
    """
    Individual unit and its conversion rate to the base unit of its category
    """
    category = models.ForeignKey(UnitCategory, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=50)  # e.g., kg, MT, m³
    base_unit = models.CharField(max_length=50)  # Base unit in this category, e.g., kg for weight
    conversion_rate = models.FloatField(default=1)  # How much 1 unit equals in base_unit
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('category', 'name')

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class EnvironmentalQuestion(models.Model):
    """
    Store environmental questions with their units dynamically
    """
    question_text = models.CharField(max_length=500)
    default_unit = models.CharField(max_length=50, default='Count')
    unit_options = models.CharField(max_length=200, help_text="Comma-separated units, e.g., MT,kg,lbs")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.order}. {self.question_text}"
    
    def get_unit_options_list(self):
        """Return unit options as a list"""
        return [u.strip() for u in self.unit_options.split(',') if u.strip()]


class MonthlyIndicatorData(models.Model):
    plant = models.ForeignKey('organizations.Plant', on_delete=models.CASCADE)
    indicator = models.CharField(max_length=255)
    month = models.CharField(max_length=3)
    value = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, default='Count')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('plant', 'indicator', 'month')
        ordering = ['indicator', 'month']
    
    def __str__(self):
        return f"{self.plant.name} - {self.indicator} - {self.month}: {self.value} {self.unit}"
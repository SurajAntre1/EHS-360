from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class UnitCategory(models.Model):
    """
    Category of units like Weight, Volume, Energy, Time, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL)

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


# Add this field to EnvironmentalQuestion model
class EnvironmentalQuestion(models.Model):
    question_text = models.CharField(max_length=500)
    unit_category = models.ForeignKey(UnitCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')  # ADD THIS
    default_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_for_questions')  # CHANGE THIS
    selected_units = models.ManyToManyField(Unit, blank=True, related_name='available_for_questions')  # ADD THIS
    # Remove or keep unit_options as backup
    unit_options = models.CharField(max_length=200, blank=True, help_text="Legacy field")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    PREDEFINED_ENV_QUESTIONS = [
        "Fatalities",
        "Lost Time Injuries (LTI)",
        "MTC (Medical Treatment Case)",
        "First aid cases",
        "Fire Incidents",
        "Near Miss Reported",
        "Near Miss Closed",
        "Observations (UA/UC) reported",
        "Observations (UA/UC) Closed",
        "Observations related to LSR/SIP reported",
        "Observations related to LSR/SIP closed",
        "Safety Inspections with Leadership Team",
        "Points Identified in leadership team reported",
        "Points Identified in leadership team closed",
        "Asbestos walkthrough carried out by plant leadership",
        "Asbestos walkthrough points reported",
        "Asbestos walkthrough points closed",
        "Total inspections carried out",
    ]
    class Meta:
        ordering = ['order', 'id']

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
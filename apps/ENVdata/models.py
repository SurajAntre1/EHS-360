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
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

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
    name = models.CharField(max_length=50)
    base_unit = models.CharField(max_length=50)
    conversion_rate = models.FloatField(default=1)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('category', 'name')

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class EnvironmentalQuestion(models.Model):
    """
    Environmental questions with dynamic filter support
    """
    question_text = models.CharField(max_length=500)
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('INCIDENT', 'Incident Module'),
            ('HAZARD', 'Hazard Module'),
            ('INSPECTION', 'Fire Inspection Module'),
            ('MANUAL', 'Manual Entry'),
        ],
        default='MANUAL'
    )
    
    # PRIMARY FILTER
    filter_field = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Primary field to filter (e.g., incident_type)"
    )
    filter_value = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Primary value to match (e.g., LTI)"
    )
    
    # SECONDARY FILTER
    filter_field_2 = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Secondary field to filter (e.g., status)"
    )
    filter_value_2 = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Secondary value to match (e.g., REPORTED)"
    )
    
    # Units (optional for auto-calculated questions)
    unit_category = models.ForeignKey(
        UnitCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='questions'
    )
    default_unit = models.ForeignKey(
        Unit, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='default_for_questions'
    )
    selected_units = models.ManyToManyField(
        Unit, 
        blank=True, 
        related_name='available_for_questions'
    )
    unit_options = models.CharField(max_length=200, blank=True, help_text="Legacy field")
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.question_text


class MonthlyIndicatorData(models.Model):
    """
    Stores monthly environmental data
    """
    MONTH_CHOICES = [
        ("JAN", "January"),
        ("FEB", "February"),
        ("MAR", "March"),
        ("APR", "April"),
        ("MAY", "May"),
        ("JUN", "June"),
        ("JUL", "July"),
        ("AUG", "August"),
        ("SEP", "September"),
        ("OCT", "October"),
        ("NOV", "November"),
        ("DEC", "December"),
    ]
    
    plant = models.ForeignKey('organizations.Plant', on_delete=models.CASCADE)
    indicator = models.ForeignKey(
        'EnvironmentalQuestion',
        on_delete=models.CASCADE,
        related_name='monthly_data',
        blank=True,null=True
    )    
    # indicator = models.CharField(max_length=100)
    month = models.CharField(max_length=3, choices=MONTH_CHOICES)
    value = models.CharField(max_length=100)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # unique_together = ('plant', 'indicator', 'month')
        ordering = ['plant', 'indicator', 'month', 'value', 'unit']
    
    def __str__(self):
        return f"{self.plant.name} - {self.indicator} - {self.month}: {self.value} {self.unit}"



class MonthlyIndicatorAttachment(models.Model):
    """
    One file attachment per plant + indicator + month cell
    """
    plant = models.ForeignKey('organizations.Plant', on_delete=models.CASCADE)
    indicator = models.ForeignKey(EnvironmentalQuestion, on_delete=models.CASCADE)
    month = models.CharField(max_length=3, choices=MonthlyIndicatorData.MONTH_CHOICES)
    file = models.FileField(upload_to='environmental/attachments/%Y/%m/')
    file_name = models.CharField(max_length=255, blank=True)  # original filename
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Enforce one file per cell
        unique_together = ('plant', 'indicator', 'month')

    def __str__(self):
        return f"{self.plant.name} - {self.indicator} - {self.month} - {self.file_name}"

    def save(self, *args, **kwargs):
        # Auto-capture original filename before saving
        if self.file and not self.file_name:
            self.file_name = self.file.name
        super().save(*args, **kwargs)        
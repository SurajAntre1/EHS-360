from django.db import models
# from django.contrib.auth.models import User
from apps.accounts.models import *
from apps.organizations.models import Plant
from django.conf import settings


class MonthlyIndicatorData(models.Model):
    MONTH_CHOICES = [
        ('jan','Jan'), ('feb','Feb'), ('mar','Mar'),
        ('apr','Apr'), ('may','May'), ('jun','Jun'),
        ('jul','Jul'), ('aug','Aug'), ('sep','Sep'),
        ('oct','Oct'), ('nov','Nov'), ('dec','Dec'),
    ]

    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name='monthly_indicators'
    )

    year = models.PositiveIntegerField(default=2025)

    month = models.CharField(
        max_length=3,
        choices=MONTH_CHOICES
    )

    indicator = models.CharField(
        max_length=255,
        help_text="Question / Indicator name"
    )

    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('plant', 'year', 'month', 'indicator')
        ordering = ['plant', 'year', 'month']

    def __str__(self):
        return f"{self.plant.name} | {self.indicator} | {self.month.upper()} {self.year}"




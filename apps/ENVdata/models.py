from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class MonthlyIndicatorData(models.Model):
    plant = models.ForeignKey('organizations.Plant', on_delete=models.CASCADE)
    indicator = models.CharField(max_length=255)
    month = models.CharField(max_length=3)  # 'jan', 'feb', etc.
    value = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, default='Count')  # NEW FIELD
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('plant', 'indicator', 'month')
        ordering = ['indicator', 'month']
    
    def __str__(self):
        return f"{self.plant.name} - {self.indicator} - {self.month}: {self.value} {self.unit}"
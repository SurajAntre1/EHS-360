from django.urls import path
from .views import *

urlpatterns = [
    path('plant-entry/',PlantMonthlyEntryView.as_view(), name='plant-entry'),
    path('questions-manager/', EnvironmentalQuestionsManagerView.as_view(), name='questions-manager'),
    path('unit-manager/',UnitManagerView.as_view(),name="unit-manager"),
]

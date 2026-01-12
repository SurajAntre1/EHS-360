from django.urls import path
from .views import PlantMonthlyEntryView

urlpatterns = [
    path('plant-entry/',PlantMonthlyEntryView.as_view(), name='plant-entry'),
]

from django.urls import path
from .views import *

app_name = 'environmental'

urlpatterns = [
    path('plant-entry/',PlantMonthlyEntryView.as_view(), name='plant-entry'),
    path('questions-manager/', EnvironmentalQuestionsManagerView.as_view(), name='questions-manager'),
    path('unit-manager/',UnitManagerView.as_view(),name="unit-manager"),
    path('api/get-category-units/', GetCategoryUnitsAPIView.as_view(), name='get-category-units'),
    # User - View Their Submitted Data (Read-only)
    path('plant-data/', PlantDataDisplayView.as_view(), name='plant-data-view'),  
    # Admin - View All Plants Data (Read-only)
    path('admin/all-plants-data/', AdminAllPlantsDataView.as_view(), name='admin-all-plants'),
    # Export to excel
    path("export_excel/", ExportExcelView.as_view(),name="export_excel"),
    # path('debug-data/', DebugDataView.as_view(), name='debug-data'),

]

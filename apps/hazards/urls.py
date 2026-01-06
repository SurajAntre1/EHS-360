# hazards/urls.py

from django.urls import path
from . import views

app_name = 'hazards'

urlpatterns = [
    # IMPORTANT: Dashboard URL ko HazardDashboardViews (plural) se link karein
    path('', views.HazardDashboardView.as_view(), name='dashboard'),
    path('hazards/dashboard/', views.HazardDashboardViews.as_view(), name='hazard_dashboard'),
    
    # ... (Aapke baki CRUD URLs) ...
    path('hazards/', views.HazardListView.as_view(), name='hazard_list'),
    path('hazards/create/', views.HazardCreateView.as_view(), name='hazard_create'),
    path('hazards/<int:pk>/', views.HazardDetailView.as_view(), name='hazard_detail'),
    path('hazards/<int:pk>/edit/', views.HazardUpdateView.as_view(), name='hazard_update'),
    
    # Action Items URLs
    path('hazards/<int:hazard_pk>/action-items/create/', views.HazardActionItemCreateView.as_view(), name='action_item_create'),
    path('action-items/<int:pk>/edit/', views.HazardActionItemUpdateView.as_view(), name='action_item_update'),

    # AJAX URLs for Cascading Dropdowns (YEH BAHUT ZARURI HAIN)
    path('ajax/get-zones/', views.GetZonesForPlantAjaxView.as_view(), name='ajax_get_zones'),
    path('ajax/get-locations/', views.GetLocationsForZoneAjaxView.as_view(), name='ajax_get_locations'),
    path('ajax/get-sublocations/', views.GetSubLocationsForLocationAjaxView.as_view(), name='ajax_get_sublocations'),
    
    # Export URL
    path('export-hazards/', views.ExportHazardsView.as_view(), name='export_hazards'),
]
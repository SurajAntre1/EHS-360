from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    path('home/', views.HomeView.as_view(), name='home'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('approvals/', views.ApprovalDashboardView.as_view(), name='approvals'),  # ADD THIS
    path('approvals/', views.ApprovalDashboardView.as_view(), name='approval_dashboard'),
    path('approvals/pending/hazards/', views.PendingHazardsListView.as_view(), name='pending_hazards_list'),
    path('approvals/pending/incidents/', views.PendingIncidentsListView.as_view(), name='pending_incidents_list'),
]
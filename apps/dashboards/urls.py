from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    path('home/', views.HomeView.as_view(), name='home'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('approvals/', views.ApprovalDashboardView.as_view(), name='approvals'),  # ADD THIS

]
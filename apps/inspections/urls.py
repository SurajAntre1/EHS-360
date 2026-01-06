
from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.inspection_dashboard, name='dashboard'),
    
    # Inspection Schedules
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/create/', views.schedule_create, name='schedule_create'),
    
    # Conduct Inspection
    path('conduct/<int:schedule_id>/', views.conduct_inspection, name='conduct_inspection'),
    
    # Inspection List & Detail
    path('inspections/', views.inspection_list, name='inspection_list'),
    path('inspections/<int:pk>/', views.inspection_detail, name='inspection_detail'),
    
    # Findings
    path('findings/', views.findings_list, name='findings_list'),
    path('findings/<int:pk>/', views.finding_detail, name='finding_detail'),
    path('findings/<int:pk>/assign/', views.finding_assign, name='finding_assign'),
    path('findings/<int:pk>/close/', views.finding_close, name='finding_close'),
    
    # Template Management (Admin)
    path('templates/', views.template_list, name='template_list'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
]
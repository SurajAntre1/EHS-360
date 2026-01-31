
from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    # Dashboard
    path('', views.inspection_dashboard, name='inspection_dashboard'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Questions
    path('questions/', views.question_list, name='question_list'),
    path('questions/create/', views.question_create, name='question_create'),
    path('questions/<int:pk>/', views.question_detail, name='question_detail'),
    path('questions/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('questions/<int:pk>/delete/', views.question_delete, name='question_delete'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/clone/', views.template_clone, name='template_clone'),
    
    # Template Questions Management
    path('templates/<int:pk>/add-question/', views.template_add_question, name='template_add_question'),
    path('templates/<int:pk>/bulk-add-questions/', views.template_bulk_add_questions, name='template_bulk_add_questions'),
    path('templates/<int:template_pk>/remove-question/<int:question_pk>/', views.template_remove_question, name='template_remove_question'),
    path('templates/<int:pk>/reorder-questions/', views.template_reorder_questions, name='template_reorder_questions'),
    
    # Schedules
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/create/', views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/', views.schedule_detail, name='schedule_detail'),
    path('schedules/<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    path('schedules/<int:pk>/cancel/', views.schedule_cancel, name='schedule_cancel'),
    path('schedules/<int:pk>/send-reminder/', views.schedule_send_reminder, name='schedule_send_reminder'),
    
    # My Inspections (for HOD)
    path('my-inspections/', views.my_inspections, name='my_inspections'),
    
    # AJAX Endpoints
    path('ajax/zones-by-plant/', views.get_zones_by_plant, name='get_zones_by_plant'),
    path('ajax/locations-by-zone/', views.get_locations_by_zone, name='get_locations_by_zone'),
    path('ajax/sublocations-by-location/', views.get_sublocations_by_location, name='get_sublocations_by_location'),
    path('ajax/questions-by-category/', views.get_questions_by_category, name='get_questions_by_category'),
]
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification Master Management
    path('master/', views.notification_master_list, name='notification_master_list'),
    path('master/create/', views.notification_master_create, name='notification_master_create'),
    path('master/<int:pk>/edit/', views.notification_master_edit, name='notification_master_edit'),
    path('master/<int:pk>/delete/', views.notification_master_delete, name='notification_master_delete'),
    path('master/<int:pk>/toggle/', views.notification_master_toggle, name='notification_master_toggle'),
    
    # AJAX endpoints
    path('get-events/', views.get_notification_events, name='get_notification_events'),
]
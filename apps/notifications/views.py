from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import NotificationMaster
from apps.accounts.models import Role


@login_required
def notification_master_list(request):
    """List all notification configurations grouped by role"""
    configurations = NotificationMaster.objects.all().select_related('role')
    
    # Group by role
    roles_with_configs = {}
    for config in configurations:
        role_name = config.role.name if config.role else "No Role"
        if role_name not in roles_with_configs:
            roles_with_configs[role_name] = []
        roles_with_configs[role_name].append(config)
    
    # Sort each role's configs by module then event
    for role in roles_with_configs:
        roles_with_configs[role] = sorted(
            roles_with_configs[role], 
            key=lambda x: (x.module, x.notification_event)
        )
    
    # Calculate statistics
    active_configs = configurations.filter(is_active=True).count()
    inactive_configs = configurations.filter(is_active=False).count()
    
    context = {
        'roles_with_configs': roles_with_configs,
        'total_configs': configurations.count(),
        'active_configs_count': active_configs,
        'inactive_configs_count': inactive_configs,
    }
    return render(request, 'notifications/master_list.html', context)

@login_required
def notification_master_create(request):
    """Create multiple notification configurations for one role"""
    if request.method == 'POST':
        role_id = request.POST.get('role')
        selected_events = request.POST.getlist('events')  # List of event codes
        
        if not role_id or not selected_events:
            messages.error(request, 'Please select a role and at least one notification event.')
            return redirect('notifications:notification_master_create')
        
        role = Role.objects.get(id=role_id)
        
        # Common settings
        reminder_type = request.POST.get('reminder_type', 'IMMEDIATE')
        days_before = int(request.POST.get('days_before_deadline', 0))
        days_after = int(request.POST.get('days_after_deadline', 0))
        filter_by_plant = request.POST.get('filter_by_plant') == 'on'
        filter_by_location = request.POST.get('filter_by_location') == 'on'
        filter_by_zone = request.POST.get('filter_by_zone') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        email_enabled = request.POST.get('email_enabled') == 'on'
        
        # Create configuration for each selected event
        created_count = 0
        skipped_count = 0
        
        for event_code in selected_events:
            # Determine module from event code
            if event_code.startswith('INCIDENT'):
                module = 'INCIDENT'
            elif event_code.startswith('HAZARD'):
                module = 'HAZARD'
            elif event_code.startswith('ENV'):
                module = 'ENVIRONMENTAL'
            elif event_code.startswith('INSPECTION'):
                module = 'INSPECTION'
            else:
                continue
            
            # Check if configuration already exists
            existing = NotificationMaster.objects.filter(
                role=role,
                notification_event=event_code
            ).exists()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create new configuration
            NotificationMaster.objects.create(
                role=role,
                module=module,
                notification_event=event_code,
                reminder_type=reminder_type,
                days_before_deadline=days_before,
                days_after_deadline=days_after,
                filter_by_plant=filter_by_plant,
                filter_by_location=filter_by_location,
                filter_by_zone=filter_by_zone,
                is_active=is_active,
                email_enabled=email_enabled,
                created_by=request.user
            )
            created_count += 1
        
        if created_count > 0:
            messages.success(request, f'Successfully created {created_count} notification configuration(s) for {role.name}!')
        if skipped_count > 0:
            messages.warning(request, f'Skipped {skipped_count} configuration(s) that already exist.')
        
        return redirect('notifications:notification_master_list')
    
    # GET request - show form
    roles = Role.objects.all()
    context = {
        'roles': roles,
        'MODULE_CHOICES': NotificationMaster.MODULE_CHOICES,
        'NOTIFICATION_EVENT_CHOICES': NotificationMaster.NOTIFICATION_EVENT_CHOICES,
        'REMINDER_TYPE_CHOICES': NotificationMaster.REMINDER_TYPE_CHOICES,
    }
    return render(request, 'notifications/master_create.html', context)


@login_required
def notification_master_edit(request, pk):
    """Edit existing notification configuration"""
    config = get_object_or_404(NotificationMaster, pk=pk)
    
    if request.method == 'POST':
        # Update configuration
        role_id = request.POST.get('role')
        config.role = Role.objects.get(id=role_id)
        config.module = request.POST.get('module')
        config.notification_event = request.POST.get('notification_event')
        config.reminder_type = request.POST.get('reminder_type')
        config.days_before_deadline = int(request.POST.get('days_before_deadline', 0))
        config.days_after_deadline = int(request.POST.get('days_after_deadline', 0))
        
        config.filter_by_plant = request.POST.get('filter_by_plant') == 'on'
        config.filter_by_location = request.POST.get('filter_by_location') == 'on'
        config.filter_by_zone = request.POST.get('filter_by_zone') == 'on'
        
        config.is_active = request.POST.get('is_active') == 'on'
        config.email_enabled = request.POST.get('email_enabled') == 'on'
        
        # Reset name to empty so save() regenerates it
        config.name = ""
        config.save()
        
        messages.success(request, f'Configuration "{config.name}" updated successfully!')
        return redirect('notifications:notification_master_list')
    
    # GET request - show form with existing data
    roles = Role.objects.all()
    
    context = {
        'config': config,
        'roles': roles,
        'MODULE_CHOICES': NotificationMaster.MODULE_CHOICES,
        'NOTIFICATION_EVENT_CHOICES': NotificationMaster.NOTIFICATION_EVENT_CHOICES,
        'REMINDER_TYPE_CHOICES': NotificationMaster.REMINDER_TYPE_CHOICES,
    }
    return render(request, 'notifications/master_edit.html', context)


@login_required
def notification_master_delete(request, pk):
    """Delete notification configuration"""
    config = get_object_or_404(NotificationMaster, pk=pk)
    
    if request.method == 'POST':
        name = config.name
        config.delete()
        messages.success(request, f'Configuration "{name}" deleted successfully!')
        return redirect('notifications:notification_master_list')
    
    return render(request, 'notifications/master_delete_confirm.html', {'config': config})


@login_required
def notification_master_toggle(request, pk):
    """Toggle active status via AJAX"""
    config = get_object_or_404(NotificationMaster, pk=pk)
    config.is_active = not config.is_active
    config.save()
    
    status = "enabled" if config.is_active else "disabled"
    return JsonResponse({'success': True, 'status': status, 'is_active': config.is_active})


@login_required
def get_notification_events(request):
    """AJAX endpoint to get notification events for selected module"""
    module = request.GET.get('module')
    
    # Filter events by module
    events = []
    for event_code, event_name in NotificationMaster.NOTIFICATION_EVENT_CHOICES:
        if event_code.startswith(module):
            events.append({'code': event_code, 'name': event_name})
    
    return JsonResponse({'events': events})
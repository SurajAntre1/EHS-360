from celery import shared_task


@shared_task(name='apps.notifications.tasks.send_investigation_overdue_notifications')
def send_investigation_overdue_notifications():
    import datetime
    from apps.accidents.models import Incident
    from apps.notifications.services import NotificationService
    
    today = datetime.date.today()
    
    overdue_incidents = Incident.objects.filter(
        investigation_required=True,
        investigation_deadline__lt=today,
        investigation_completed_date__isnull=True,
    ).exclude(
        status='CLOSED'
    ).select_related(
        'plant', 'zone', 'location',
        'reported_by', 'incident_type'
    )
    
    total = overdue_incidents.count()
    
    if total == 0:
        print("✅ No overdue investigations found today.")
        return "No overdue investigations found."
    
    print(f"⚠️ Found {total} overdue investigation(s). Sending notifications...")
    
    success_count = 0
    error_count = 0
    
    for incident in overdue_incidents:
        try:
            extra_recipients = []
            
            if incident.reported_by:
                extra_recipients.append(incident.reported_by)
            
            if incident.investigator:
                extra_recipients.append(incident.investigator)
            
            NotificationService.notify(
                content_object=incident,
                notification_type='INCIDENT_INVESTIGATION_OVERDUE',
                module='INVESTIGATION_OVERDUE',
                extra_recipients=extra_recipients if extra_recipients else None
            )
            
            success_count += 1
            print(f"  ✅ Notification sent for: {incident.report_number}")
            
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error for {incident.report_number}: {e}")
    
    result = f"Overdue notifications — Sent: {success_count}, Errors: {error_count}, Total: {total}"
    print(result)
    return result
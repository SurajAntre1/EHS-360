from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accidents.models import Incident
from apps.accidents.notifications import notify_investigation_due_soon, notify_investigation_overdue
import datetime


class Command(BaseCommand):
    help = 'Send reminder notifications for pending investigations'
    
    def handle(self, *args, **options):
        today = datetime.date.today()
        
        # Find incidents with investigation due in 1 day
        due_soon = Incident.objects.filter(
            investigation_required=True,
            investigation_completed_date__isnull=True,
            investigation_deadline=today + datetime.timedelta(days=1)
        )
        
        for incident in due_soon:
            notify_investigation_due_soon(incident, days_remaining=1)
            self.stdout.write(f"Sent reminder for {incident.report_number}")
        
        # Find overdue investigations
        overdue = Incident.objects.filter(
            investigation_required=True,
            investigation_completed_date__isnull=True,
            investigation_deadline__lt=today
        )
        
        for incident in overdue:
            notify_investigation_overdue(incident)
            self.stdout.write(f"Sent overdue alert for {incident.report_number}")
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import NotificationMaster, Notification
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """
    Generic notification service that uses NotificationMaster configurations
    """
    
    @staticmethod
    def get_stakeholders_for_event(event_type, plant=None, location=None, zone=None):
        """
        Get stakeholders based on NotificationMaster configuration
        
        Args:
            event_type: Notification event type (e.g., 'INCIDENT_REPORTED')
            plant: Plant object
            location: Location object
            zone: Zone object
        
        Returns:
            List of User objects who should receive this notification
        """
        print(f"\n{'='*70}")
        print(f"FINDING STAKEHOLDERS FOR: {event_type}")
        print(f"{'='*70}")
        print(f"Plant: {plant}")
        print(f"Location: {location}")
        print(f"Zone: {zone}")
        
        # Get all active notification configurations for this event type
        configs = NotificationMaster.objects.filter(
            notification_event=event_type,
            is_active=True
        ).select_related('role')
        
        if not configs.exists():
            print(f"⚠️ No notification configurations found for {event_type}")
            return []
        
        print(f"\nFound {configs.count()} active configuration(s)")
        
        stakeholders = []
        
        for config in configs:
            print(f"\n--- Processing Config: {config.name} ---")
            print(f"Role: {config.role.name}")
            print(f"Filters: Plant={config.filter_by_plant}, Location={config.filter_by_location}, Zone={config.filter_by_zone}")
            
            # Build query to find users with this role
            query = User.objects.filter(
                role=config.role,
                is_active=True
            )
            
            # Apply filters based on configuration
            if config.filter_by_plant and plant:
                query = query.filter(plant=plant)
                print(f"  - Filtered by plant: {plant.name}")
            
            if config.filter_by_location and location:
                query = query.filter(location=location)
                print(f"  - Filtered by location: {location.name}")
            
            if config.filter_by_zone and zone:
                query = query.filter(zone=zone)
                print(f"  - Filtered by zone: {zone.name}")
            
            users = query.all()
            print(f"  - Found {users.count()} user(s) with role {config.role.name}")
            
            for user in users:
                print(f"    • {user.username} | {user.get_full_name()} | {user.email}")
                if user not in stakeholders:
                    stakeholders.append(user)
        
        print(f"\n{'='*70}")
        print(f"TOTAL UNIQUE STAKEHOLDERS: {len(stakeholders)}")
        print(f"{'='*70}\n")
        
        return stakeholders
    
    
    @staticmethod
    def create_notification(recipient, content_object, notification_type, title, message):
        """
        Create a notification in the database
        
        Args:
            recipient: User object
            content_object: The object (Incident/Hazard) being notified about
            notification_type: Type of notification
            title: Notification title
            message: Notification message
        """
        print(f"\n--- CREATING NOTIFICATION ---")
        print(f"Recipient: {recipient.username}")
        print(f"Type: {notification_type}")
        print(f"Title: {title[:50]}...")
        
        try:
            content_type = ContentType.objects.get_for_model(content_object)
            
            notification = Notification(
                recipient=recipient,
                content_type=content_type,
                object_id=content_object.id,
                notification_type=notification_type,
                title=title,
                message=message,
                is_read=False
            )
            
            notification.save()
            print(f"  ✅ SAVED! Notification ID: {notification.id}")
            return notification
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    
    @staticmethod
    def send_email(recipient, subject, message, html_template=None, context=None):
        """
        Send email notification
        
        Args:
            recipient: User object
            subject: Email subject
            message: Plain text message
            html_template: Path to HTML template (optional)
            context: Template context dictionary (optional)
        """
        print(f"\n--- SENDING EMAIL ---")
        print(f"To: {recipient.email}")
        print(f"Subject: {subject}")
        
        # Check if email is configured
        if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
            print("  ⚠️ EMAIL NOT CONFIGURED - Skipping email send")
            return False
        
        try:
            # Render HTML template if provided
            if html_template and context:
                html_content = render_to_string(html_template, context)
            else:
                html_content = None
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient.email]
            )
            
            if html_content:
                email.attach_alternative(html_content, "text/html")
            
            email.send(fail_silently=False)
            print("  ✅ Email sent successfully")
            return True
            
        except Exception as e:
            print(f"  ❌ Email error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    
    @staticmethod
    def notify(content_object, notification_type, module='INCIDENT'):
        """
        Main notification function - finds stakeholders and sends notifications
        
        Args:
            content_object: The object (Incident/Hazard) being notified about
            notification_type: Type of notification (e.g., 'INCIDENT_REPORTED')
            module: Module name for template selection
        """
        print("\n" + "*"*70)
        print(f"NOTIFICATION SYSTEM - {notification_type}")
        print("*"*70)
        
        # Get plant, location, zone from content object
        plant = getattr(content_object, 'plant', None)
        location = getattr(content_object, 'location', None)
        zone = getattr(content_object, 'zone', None)
        
        # Find stakeholders based on NotificationMaster configuration
        stakeholders = NotificationService.get_stakeholders_for_event(
            event_type=notification_type,
            plant=plant,
            location=location,
            zone=zone
        )
        
        if not stakeholders:
            print("\n❌ ERROR: No stakeholders found!")
            return
        
        # Get notification configuration
        config = NotificationMaster.objects.filter(
            notification_event=notification_type,
            is_active=True
        ).first()
        
        # Build notification content
        if module == 'INCIDENT':
            context = NotificationService._build_incident_context(content_object)
        elif module == 'HAZARD':
            context = NotificationService._build_hazard_context(content_object)
        else:
            context = {'object': content_object}
        
        # Send notifications to each stakeholder
        notifications_created = 0
        emails_sent = 0
        
        for stakeholder in stakeholders:
            print(f"\n{'='*70}")
            print(f"STAKEHOLDER: {stakeholder.username}")
            print(f"{'='*70}")
            
            # Create in-app notification
            notification = NotificationService.create_notification(
                recipient=stakeholder,
                content_object=content_object,
                notification_type=notification_type,
                title=context.get('title', ''),
                message=context.get('message', '')
            )
            
            if notification:
                notifications_created += 1
            
            # Send email if enabled in configuration
            if config and config.email_enabled:
                context['recipient'] = stakeholder
                email_sent = NotificationService.send_email(
                    recipient=stakeholder,
                    subject=context.get('subject', ''),
                    message=context.get('message', ''),
                    html_template=f'emails/{module.lower()}/notification.html',
                    context=context
                )
                
                if email_sent:
                    emails_sent += 1
                    if notification:
                        notification.is_email_sent = True
                        notification.email_sent_at = timezone.now()
                        notification.save()
        
        print(f"\n{'='*70}")
        print("NOTIFICATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total stakeholders: {len(stakeholders)}")
        print(f"Notifications created: {notifications_created}")
        print(f"Emails sent: {emails_sent}")
        print(f"{'='*70}\n")
    
    
    @staticmethod
    def _build_incident_context(incident):
        """Build context for incident notifications"""
        return {
            'title': f"New Incident Reported | {incident.report_number}",
            'subject': f"⚠️ New Incident Reported - {incident.report_number}",
            'message': f"""
Hello,

A new {incident.get_incident_type_display()} has been reported.

INCIDENT DETAILS
--------------------------------------------------
Incident Number      : {incident.report_number}
Date & Time          : {incident.incident_date} {incident.incident_time}
Plant                : {incident.plant.name}
Location             : {incident.location.name if incident.location else 'N/A'}
Reported By          : {incident.reported_by.get_full_name()}
Investigation Deadline: {incident.investigation_deadline}

DESCRIPTION
--------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

Please review this incident and take necessary action.

Regards,
EHS Management System
""",
            'incident': incident,
        }
    
    
    @staticmethod
    def _build_hazard_context(hazard):
        """Build context for hazard notifications"""
        return {
            'title': f"New Hazard Reported | {hazard.report_number}",
            'subject': f"⚠️ New Hazard Reported - {hazard.report_number}",
            'message': f"""
Hello,

A new hazard has been reported.

HAZARD DETAILS
--------------------------------------------------
Hazard Number   : {hazard.report_number}
Type            : {hazard.get_hazard_type_display()}
Severity        : {hazard.get_severity_display()}
Plant           : {hazard.plant.name}
Location        : {hazard.location.name if hazard.location else 'N/A'}
Reported By     : {hazard.reported_by.get_full_name()}

DESCRIPTION
--------------------------------------------------
{hazard.hazard_description[:300]}{'...' if len(hazard.hazard_description) > 300 else ''}

Please review and take necessary action.

Regards,
EHS Management System
""",
            'hazard': hazard,
        }
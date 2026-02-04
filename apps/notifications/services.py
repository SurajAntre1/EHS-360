from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import NotificationMaster, Notification
from apps.accidents.models import IncidentType
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
            
            if config.role.name == 'PLANT HEAD':
                config.filter_by_plant = True
                
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
            content_object: The object (Incident/Hazard/InvestigationReport) being notified about
            notification_type: Type of notification (e.g., 'INCIDENT_REPORTED')
            module: Module name for template selection
        """
        print("\n" + "*"*70)
        print(f"NOTIFICATION SYSTEM - {notification_type}")
        print("*"*70)

        if content_object is None:
            print(f"\n❌ ERROR: content_object is None. Cannot send notification for {notification_type}")
            return

        # Determine object type and extract plant/location/zone
        # Auto-detect object type
        if hasattr(content_object, 'incident'):
            # Investigation Report
            incident = content_object.incident
            plant = incident.plant
            location = incident.location
            zone = incident.zone
        elif hasattr(content_object, 'hazard'):
            hazard = content_object.hazard
            plant = hazard.plant
            location = hazard.location
            zone = hazard.zone
        else:
            # Incident / Hazard
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

        notifications_created = 0
        emails_sent = 0
        # Build notification context
        if hasattr(content_object, 'incident'):
            context = NotificationService._build_incident_report_context(content_object)
        elif hasattr(content_object, 'hazard'):
            context = NotificationService._build_hazard_action_context(content_object)
        elif module == 'HAZARD':
            context = NotificationService._build_hazard_context(content_object)
        elif module == 'ENV':
            context = NotificationService._build_environment_context(content_object)
        elif module == 'INCIDENT_CLOSED':    
            context = NotificationService._build_incident_close_context(content_object)
        elif module == 'INSPECTION' and notification_type == 'NOTIFY_INSPECTION':
            context = NotificationService._build_notify_inspection_context(content_object)
        elif module == 'INSPECTION':
            context = NotificationService._build_inspection_context(content_object)
        else:
            context = NotificationService._build_incident_context(content_object)


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

            # Check role config for email
            role_config = NotificationMaster.objects.filter(
                notification_event=notification_type,
                role=stakeholder.role,
                is_active=True
            ).first()

            if role_config and getattr(role_config, 'email_enabled', False):
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
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        return {
            'title': f"New Incident Reported | {incident.report_number}",
            'subject': f"⚠️ New Incident Reported - {incident.report_number}",
            'message': f"""
Hello,

A new {incident_type} has been reported.

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
    
    @staticmethod
    def _build_incident_report_context(incidentinvestigationreport):
        """
        Build context for Incident Investigation Report notifications
        """
        incident = incidentinvestigationreport.incident
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        return {
            'title': f"Incident Investigation Completed | {incident.report_number}",
            'subject': f"📝 Investigation Report Submitted - {incident.report_number}",
            'message': f"""
Hello,
The investigation report for the following incident has been completed and submitted.

INCIDENT DETAILS
--------------------------------------------------
Incident Number      : {incident.report_number}
Incident Type        : {incident_type}
Date & Time          : {incident.incident_date} {incident.incident_time}
Plant                : {incident.plant.name}
Zone                 : {incident.zone.name if incident.zone else 'N/A'}
Location             : {incident.location.name if incident.location else 'N/A'}
Sub-Location         : {incident.sublocation.name if incident.sublocation else 'N/A'}
Reported By          : {incident.reported_by.get_full_name()}
Investigation Date   : {incidentinvestigationreport.investigation_date}
Investigator         : {incidentinvestigationreport.investigator.get_full_name()}
Completed On         : {incidentinvestigationreport.completed_date}

INCIDENT DESCRIPTION
--------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

KEY FINDINGS
--------------------------------------------------
Sequence of Events:
{incidentinvestigationreport.sequence_of_events[:300]}{'...' if len(incidentinvestigationreport.sequence_of_events) > 300 else ''}

Root Cause Analysis:
{incidentinvestigationreport.root_cause_analysis[:300]}{'...' if len(incidentinvestigationreport.root_cause_analysis) > 300 else ''}

RECOMMENDATIONS
--------------------------------------------------
Immediate Corrective Actions:
{incidentinvestigationreport.immediate_corrective_actions[:300]}{'...' if len(incidentinvestigationreport.immediate_corrective_actions) > 300 else ''}

Preventive Measures:
{incidentinvestigationreport.preventive_measures[:300]}{'...' if len(incidentinvestigationreport.preventive_measures) > 300 else ''}

Please review the investigation findings and proceed with action item assignment if required.

Regards,
EHS Management System
""",
        'investigation_report': incidentinvestigationreport,
        'incident':incident,
    }


    @staticmethod
    def _build_incident_close_context(incident):
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        """Build context for incident closure notifications"""
        return{
            'title' : f"Incident Closed | {incident.report_number}",
            'subject' : f"Incident Closed ✅ - {incident.report_number}",
            'message' : f"""
Hello,

A {incident_type} has been closed.

INCIDENT DETAILS 
----------------------------------------------------------------------------------
Incident Number     : {incident.report_number}
Date & Time         : {incident.incident_date} {incident.incident_time}
Plant               : {incident.plant.name}
Location            : {incident.location.name}
Closed By           : {incident.closed_by.get_full_name()}
Closure Date        : {incident.closure_date}

DESCRIPTION
---------------------------------------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

Regards,
EHS Management System
""",

            'incident':incident,
        }
    
    @staticmethod
    def _build_incident_action_context(incidnetactionitem):
        """
        Build context for Incident Action notifications
        """
        incident = incidnetactionitem.incident  
        incident_type = (
            incident.incident_type.name
            if incident.incident_type else 'NA'
        )
        return {
            'title' : f"Incident Action Assigned | {incident.report_number}",
            'subject': f"✅ Incident Action Assigned - {incident.report_number}",
            'message': f"""
Hello,
The investigation action for the following incident has been assigned.

INCIDENT DETAILS
------------------------------------------------------------------
Incident Number      : {incident.report_number}
Incident Type        : {incident_type}
Date & Time          : {incident.incident_date} {incident.incident_time}
Plant                : {incident.plant.name}
Zone                 : {incident.zone.name if incident.zone else 'N/A'}
Location             : {incident.location.name if incident.location else 'N/A'}
Sub-Location         : {incident.sublocation.name if incident.sublocation else 'N/A'}
Reported By          : {incident.reported_by.get_full_name()}
Target Date          : {incidnetactionitem.target_date}
Status               : {incidnetactionitem.status}
Completion Date      : {incidnetactionitem.completion_date}

INCIDENT DESCRIPTION
--------------------------------------------------
{incident.description[:300]}{'...' if len(incident.description) > 300 else ''}

ACTION DESCRIPTION
--------------------------------------------------
{incidnetactionitem.description[:300]}{'...' if len(incidnetactionitem.description) > 300 else ''}

Regards,
EHS Management System
""",
            'incidnetactionitem':incidnetactionitem,
            'incident':incident,
        }
    

    @staticmethod
    def _build_hazard_action_context(action_item):
        hazard = action_item.hazard

        return {
            'title': f"Hazard Action Assigned | {hazard.report_number}",
            'subject': f"⚠️ Hazard Action Assigned - {hazard.report_number}",

            'message': f"""
Hello,

A hazard action item has been assigned to you.

HAZARD DETAILS
--------------------------------------------------
Hazard Number     : {hazard.report_number}
Hazard Type       : {hazard.get_hazard_type_display()}
Reported Date     : {hazard.reported_date}
Plant             : {hazard.plant.name}
Zone              : {hazard.zone.name if hazard.zone else 'N/A'}
Location          : {hazard.location.name if hazard.location else 'N/A'}
Sub-Location      : {hazard.sublocation.name if hazard.sublocation else 'N/A'}

ACTION DETAILS
--------------------------------------------------
Description       : {action_item.action_description}
Target Date       : {action_item.target_date}
Status            : {action_item.status}

Please complete the action within the target date.

Regards,
EHS Management System
""",
            'hazard': hazard,
            'action_item': action_item,
        }
    
    def _build_environment_context(plant):
        return{
            'title': f"Enviromental Data Submitted | {plant.name}",
            'subject': f"🌱 Environmental Data Submitted - {plant.name}",
            'message': f"""
Hello,

Monthly environmental data has been submitted successfully.

PLANT DETAILS
--------------------------------------------------
Plant Name : {plant.name}

Please review the submitted enviromental data.

Regards,
EHS Management System
""",
            'plant':plant,
        }
    
    def _build_inspection_context(schedule):
        return{
            'title': f"Inspection {schedule.get_status_display()} | {schedule.schedule_code}",
            'subject': f"📝 Inspection {schedule.get_status_display()} - {schedule.schedule_code}",
            'message': f"""
Hello,

An inspection update has occurred.

INSPECTION DETAILS
--------------------------------------------------
Schedule Code      : {schedule.schedule_code}
Template           : {schedule.template.template_name}
Inspection Type    : {schedule.template.get_inspection_type_display()}
Plant              : {schedule.plant.name}
Department         : {schedule.department.name if schedule.department else 'N/A'}

ASSIGNED DETAILS
--------------------------------------------------
Assigned To        : {schedule.assigned_to.get_full_name()}
Assigned By        : {schedule.assigned_by.get_full_name()}
Scheduled Date     : {schedule.scheduled_date}
Due Date           : {schedule.due_date}

STATUS
--------------------------------------------------
Current Status     : {schedule.get_status_display()}

Please log in to the EHS system for more details.

Regards,
EHS Management System
""",
        'schedule': schedule,
    }


    def _build_notify_inspection_context(schedule):
        return{
            'title': f"Inspection Reminder | {schedule.schedule_code}",
            'subject': f"⏰ Reminder: Inspection {schedule.get_status_display()} - {schedule.schedule_code}",
            'message': f"""

Hello {schedule.assigned_to.get_full_name()},

This is a reminder regarding the upcoming inspection.

INSPECTION DETAILS
--------------------------------------------------
Schedule Code      : {schedule.schedule_code}
Template           : {schedule.template.template_name}
Inspection Type    : {schedule.template.get_inspection_type_display()}
Plant              : {schedule.plant.name}
Department         : {schedule.department.name if schedule.department else 'N/A'}
Assigned By        : {schedule.assigned_by.get_full_name()}
Scheduled Date     : {schedule.scheduled_date}
Due Date           : {schedule.due_date}
Current Status     : {schedule.get_status_display()}

Please ensure the inspection is completed within the scheduled timeframe.

Regards,
EHS Management System
""",
        'schedule': schedule,
        'recipient': schedule.assigned_to,
    }

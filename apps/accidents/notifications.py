from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Incident
from .models import *
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def get_incident_stakeholders(incident):
    """Get all stakeholders who should be notified about this incident"""
    print("\n" + "=" * 70)
    print("STEP 1: FINDING STAKEHOLDERS")
    print("=" * 70)
    print(f"Incident: {incident.report_number}")
    print(f"Plant: {incident.plant} (ID: {incident.plant.id if incident.plant else None})")
    print(f"Location: {incident.location} (ID: {incident.location.id if incident.location else None})")
    
    stakeholders = []
    
    # 1. Safety Managers
    print("\n--- Looking for SAFETY_MANAGER ---")
    if incident.plant:
        safety_managers = User.objects.filter(
            plant=incident.plant,
            role='SAFETY_MANAGER',
            is_active=True
        )
        print(f"Query: User.objects.filter(plant={incident.plant.id}, role='SAFETY_MANAGER', is_active=True)")
        print(f"Found: {safety_managers.count()} Safety Managers")
        for sm in safety_managers:
            print(f"  - {sm.username} | {sm.get_full_name()} | {sm.email}")
            stakeholders.append(sm)
    
    # 2. Location Heads
    print("\n--- Looking for LOCATION_HEAD ---")
    if incident.location:
        location_heads = User.objects.filter(
            location=incident.location,
            role='LOCATION_HEAD',
            is_active=True
        )
        print(f"Query: User.objects.filter(location={incident.location.id}, role='LOCATION_HEAD', is_active=True)")
        print(f"Found: {location_heads.count()} Location Heads")
        for lh in location_heads:
            print(f"  - {lh.username} | {lh.get_full_name()} | {lh.email}")
            stakeholders.append(lh)
    else:
        print("  Location is None - skipping")
    
    # 3. Plant Heads
    print("\n--- Looking for PLANT_HEAD ---")
    if incident.plant:
        plant_heads = User.objects.filter(
            plant=incident.plant,
            role='PLANT_HEAD',
            is_active=True
        )
        print(f"Query: User.objects.filter(plant={incident.plant.id}, role='PLANT_HEAD', is_active=True)")
        print(f"Found: {plant_heads.count()} Plant Heads")
        for ph in plant_heads:
            print(f"  - {ph.username} | {ph.get_full_name()} | {ph.email}")
            stakeholders.append(ph)
    
    # 4. Admins of same plant
    print("\n--- Looking for ADMIN ---")
    if incident.plant:
        admins = User.objects.filter(
            plant=incident.plant,
            role='ADMIN',
            is_active=True
        )
        print(f"Query: User.objects.filter(plant={incident.plant.id}, role='ADMIN', is_active=True)")
        print(f"Found: {admins.count()} Admins")
        for admin in admins:
            print(f"  - {admin.username} | {admin.get_full_name()} | {admin.email}")
            stakeholders.append(admin)
    
    # 5. Fallback to superusers
    if not stakeholders:
        print("\n--- No plant-specific stakeholders found! Using SUPERUSER fallback ---")
        superusers = User.objects.filter(is_superuser=True, is_active=True)
        print(f"Query: User.objects.filter(is_superuser=True, is_active=True)")
        print(f"Found: {superusers.count()} Superusers")
        for su in superusers:
            print(f"  - {su.username} | {su.get_full_name()} | {su.email}")
            stakeholders.append(su)
    
    unique_stakeholders = list(set(stakeholders))
    print("\n" + "=" * 70)
    print(f"TOTAL UNIQUE STAKEHOLDERS: {len(unique_stakeholders)}")
    print("=" * 70)
    
    return unique_stakeholders


def create_notification_in_db(recipient, incident, notification_type, title, message):
    """Create notification with detailed logging"""
    print(f"\n--- CREATING NOTIFICATION IN DATABASE ---")
    print(f"Recipient: {recipient.username} (ID: {recipient.id})")
    print(f"Incident: {incident.report_number} (ID: {incident.id})")
    print(f"Type: {notification_type}")
    print(f"Title: {title[:50]}...")
    
    try:
        # Check if IncidentNotification model is available
        print("Checking IncidentNotification model...")
        from apps.accidents.notification_models import IncidentNotification as NotifModel
        print(f"  ✅ Model imported: {NotifModel}")
        
        # Create the notification
        print("Creating notification object...")
        notification = NotifModel(
            recipient=recipient,
            incident=incident,
            notification_type=notification_type,
            title=title,
            message=message,
            is_read=False
        )
        print(f"  ✅ Notification object created (not saved yet)")
        
        # Save to database
        print("Saving to database...")
        notification.save()
        print(f"  ✅ SAVED! Notification ID: {notification.id}")
        
        # Verify it's actually in the database
        print("Verifying in database...")
        check = NotifModel.objects.filter(id=notification.id).first()
        if check:
            print(f"  ✅ VERIFIED in database: ID={check.id}")
            return notification
        else:
            print(f"  ❌ NOT FOUND in database after save!")
            return None
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def send_email_to_stakeholder(recipient, incident, message):
    """Send email notification"""
    print(f"\n--- SENDING EMAIL ---")
    print(f"To: {recipient.email}")
    print(f"Recipient: {recipient.get_full_name()}")
    
    # Check if email is configured
    if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
        print("  ⚠️ EMAIL NOT CONFIGURED - Skipping email send")
        print("  Add EMAIL_HOST, EMAIL_PORT, etc. to settings.py to enable emails")
        return False
    
    try:
        subject = f"⚠️ New Incident Reported - {incident.report_number}"
        
        # Simple text email for now
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email]
        )
        
        print(f"  Sending email...")
        email.send(fail_silently=False)
        print(f"  ✅ Email sent successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Email error: {e}")
        import traceback
        traceback.print_exc()
        return False


def notify_incident_reported(incident):
    """Notify stakeholders when incident is reported"""
    print("\n\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 20 + "NOTIFICATION SYSTEM" + " " * 29 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print(f"\nIncident: {incident.report_number}")
    print(f"Created at: {incident.created_at}")
    print(f"Reported by: {incident.reported_by.get_full_name()}")
    
    # STEP 1: Find stakeholders
    stakeholders = get_incident_stakeholders(incident)
    
    if not stakeholders:
        print("\n❌ ERROR: No stakeholders found!")
        print("Cannot send notifications - no users to notify!")
        print("*" * 70)
        return
    
    # STEP 2: Create notifications and send emails
    print("\n" + "=" * 70)
    print("STEP 2: CREATING NOTIFICATIONS & SENDING EMAILS")
    print("=" * 70)
    
    notifications_created = 0
    emails_sent = 0
    
    for idx, stakeholder in enumerate(stakeholders, 1):
        print(f"\n{'=' * 70}")
        print(f"STAKEHOLDER {idx}/{len(stakeholders)}: {stakeholder.username}")
        print(f"{'=' * 70}")
        
        title = f"New Incident Reported: {incident.report_number}"
        message = f"""A new {incident.get_incident_type_display()} has been reported.

Incident Number: {incident.report_number}
Date & Time: {incident.incident_date} at {incident.incident_time}
Plant: {incident.plant.name}
Location: {incident.location.name if incident.location else 'N/A'}
Reported by: {incident.reported_by.get_full_name()}
Investigation Deadline: {incident.investigation_deadline}

Description: {incident.description[:200]}...

Please review this incident and take necessary action.
"""
        
        # Create in-app notification
        notification = create_notification_in_db(
            recipient=stakeholder,
            incident=incident,
            notification_type='INCIDENT_REPORTED',
            title=title,
            message=message
        )
        
        if notification:
            notifications_created += 1
        
        # Send email
        email_sent = send_email_to_stakeholder(
            recipient=stakeholder,
            incident=incident,
            message=message
        )
        
        if email_sent:
            emails_sent += 1
    
    # STEP 3: Summary
    print("\n\n" + "=" * 70)
    print("NOTIFICATION SUMMARY")
    print("=" * 70)
    print(f"Total stakeholders found: {len(stakeholders)}")
    print(f"Notifications created: {notifications_created}")
    print(f"Emails sent: {emails_sent}")
    print("=" * 70)
    print("\n")
    
    # STEP 4: Verify in database
    print("=" * 70)
    print("DATABASE VERIFICATION")
    print("=" * 70)
    total_notifications = IncidentNotification.objects.filter(incident=incident).count()
    print(f"Notifications in database for this incident: {total_notifications}")
    
    if total_notifications > 0:
        print("\nNotifications found:")
        for notif in IncidentNotification.objects.filter(incident=incident):
            print(f"  - ID: {notif.id} | Recipient: {notif.recipient.username} | Read: {notif.is_read}")
    else:
        print("⚠️ NO NOTIFICATIONS FOUND IN DATABASE!")
    
    print("=" * 70)
    print("*" * 70)
    print("\n\n")
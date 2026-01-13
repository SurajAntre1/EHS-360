from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Hazard, HazardNotification
from .models import *
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def get_hazard_stakeholders(hazard):
    """Get all stakeholders who should be notified about this hazard"""
    print("\n" + "=" * 70)
    print("STEP 1: FINDING STAKEHOLDERS")
    print("=" * 70)
    print(f"hazard: {hazard.report_number}")
    print(f"Plant: {hazard.plant} (ID: {hazard.plant.id if hazard.plant else None})")
    print(f"Location: {hazard.location} (ID: {hazard.location.id if hazard.location else None})")
    
    stakeholders = []
    
    # 1. Safety Managers
    print("\n--- Looking for SAFETY_MANAGER ---")
    if hazard.plant:
        safety_managers = User.objects.filter(
            plant=hazard.plant,
            role__name='SAFETY MANAGER',
            is_active=True
        )
        print(f"Query: User.objects.filter(plant={hazard.plant.id}, role='SAFETY MANAGER', is_active=True)")
        print(f"Found: {safety_managers.count()} Safety Managers")
        for sm in safety_managers:
            print(f"  - {sm.username} | {sm.get_full_name()} | {sm.email}")
            stakeholders.append(sm)
    
    # 2. Location Heads
    print("\n--- Looking for LOCATION_HEAD ---")
    if hazard.location:
        location_heads = User.objects.filter(
            location=hazard.location,
            role__name='LOCATION HEAD',
            is_active=True
        )
        print(f"Query: User.objects.filter(location={hazard.location.id}, role='LOCATION_HEAD', is_active=True)")
        print(f"Found: {location_heads.count()} Location Heads")
        for lh in location_heads:
            print(f"  - {lh.username} | {lh.get_full_name()} | {lh.email}")
            stakeholders.append(lh)
    else:
        print("  Location is None - skipping")
    
    # 3. Plant Heads
    print("\n--- Looking for PLANT_HEAD ---")
    if hazard.plant:
        plant_heads = User.objects.filter(
            plant=hazard.plant,
            role__name='PLANT HEAD',
            is_active=True
        )
        print(f"Query: User.objects.filter(plant={hazard.plant.id}, role='PLANT_HEAD', is_active=True)")
        print(f"Found: {plant_heads.count()} Plant Heads")
        for ph in plant_heads:
            print(f"  - {ph.username} | {ph.get_full_name()} | {ph.email}")
            stakeholders.append(ph)
    
    # 4. Admins of same plant
    print("\n--- Looking for ADMIN ---")
    if hazard.plant:
        admins = User.objects.filter(
            plant=hazard.plant,
            role__name='ADMIN',
            is_active=True
        )
        print(f"Query: User.objects.filter(plant={hazard.plant.id}, role='ADMIN', is_active=True)")
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


def create_notification_in_db(recipient, hazard, notification_type, title, message):
    """Create notification with detailed logging"""
    print(f"\n--- CREATING NOTIFICATION IN DATABASE ---")
    print(f"Recipient: {recipient.username} (ID: {recipient.id})")
    print(f"hazard: {hazard.report_number} (ID: {hazard.id})")
    print(f"Type: {notification_type}")
    print(f"Title: {title[:50]}...")
    
    try:
        # Check if hazardNotification model is available
        print("Checking hazardNotification model...")
        from apps.hazards.notification_models import hazardNotification as NotifModel
        print(f"  ✅ Model imported: {NotifModel}")
        
        # Create the notification
        print("Creating notification object...")
        notification = NotifModel(
            recipient=recipient,
            hazard=hazard,
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


def send_email_to_stakeholder(recipient, hazard, message):
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
        subject = f"⚠️ New hazard Reported - {hazard.report_number}"
        
        # Sending email
        email = {
            "hazard" : hazard,
            "hazard_type"  : hazard.get_hazard_type_display(),
            "location" : hazard.location.name if hazard.location else "N/A",
             "description": hazard.description[:300] + (
                "..." if len(hazard.description) > 300 else ""
            ),
        }

        html_content = render_to_string(
            "emails/hazard_notification.html",
            email
        )
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,  
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email]
        )

        email.attach_alternative(html_content, "text/html")
        print("  Sending email...")
        email.send(fail_silently=False)
        print("  ✅ Email sent successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Email error: {e}")
        import traceback
        traceback.print_exc()
        return False


def notify_hazard_reported(hazard):
    """Notify stakeholders when hazard is reported"""
    print("\n\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 20 + "NOTIFICATION SYSTEM" + " " * 29 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print(f"\nhazard: {hazard.report_number}")
    print(f"Created at: {hazard.created_at}")
    print(f"Reported by: {hazard.reported_by.get_full_name()}")
    
    # STEP 1: Find stakeholders
    stakeholders = get_hazard_stakeholders(hazard)
    
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
        
        title = f"New hazard Reported | {hazard.report_number}"
        message = message = f"""
Hello,
A new {hazard.get_hazard_type_display()} has been reported. Please find the details below:

--------------------------------------------------
hazard DETAILS
--------------------------------------------------
hazard Number      : {hazard.report_number}
Date & Time          : {hazard.hazard_date} {hazard.hazard_time}
Plant                : {hazard.plant.name}
Location             : {hazard.location.name if hazard.location else 'N/A'}
Reported By          : {hazard.reported_by.get_full_name()}
Investigation Deadline: {hazard.investigation_deadline}

--------------------------------------------------
DESCRIPTION           
--------------------------------------------------
{hazard.description[:300]}{'...' if len(hazard.description) > 300 else ''}

--------------------------------------------------
ACTION REQUIRED
--------------------------------------------------
Please review this hazard and take necessary action.

Regards,
EHS Management System
"""
        
        # Create in-app notification
        notification = create_notification_in_db(
            recipient=stakeholder,
            hazard=hazard,
            notification_type='HAZARD_REPORTED',
            title=title,
            message=message
        )
        
        if notification:
            notifications_created += 1
        
        # Send email
        email_sent = send_email_to_stakeholder(
            recipient=stakeholder,
            hazard=hazard,
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
    total_notifications = HazardNotification.objects.filter(hazard=hazard).count()
    print(f"Notifications in database for this hazard: {total_notifications}")
    
    if total_notifications > 0:
        print("\nNotifications found:")
        for notif in HazardNotification.objects.filter(hazard=hazard):
            print(f"  - ID: {notif.id} | Recipient: {notif.recipient.username} | Read: {notif.is_read}")
    else:
        print("⚠️ NO NOTIFICATIONS FOUND IN DATABASE!")
    
    print("=" * 70)
    print("*" * 70)
    print("\n\n")
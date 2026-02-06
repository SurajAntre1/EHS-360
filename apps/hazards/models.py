from django.db import models
from django.contrib.auth import get_user_model
from apps.organizations.models import *
import datetime
from django.utils import timezone

User = get_user_model()


class Hazard(models.Model):
    """
    Hazard Reporting Model
    Supports hazard identification and management
    """
    
    # Detailed Hazard Categories (16 types)
    HAZARD_CATEGORIES = [
        ('slip_trip_fall', 'Slip/Trip/Fall'),
        ('chemical', 'Chemical'),
        ('electrical', 'Electrical'),
        ('fire', 'Fire'),
        ('equipment', 'Equipment/Machinery'),
        ('ergonomic', 'Ergonomic'),
        ('biological', 'Biological'),
        ('environmental', 'Environmental'),
        ('confined_space', 'Confined Space'),
        ('working_at_height', 'Working at Height'),
        ('manual_handling', 'Manual Handling'),
        ('noise', 'Noise/Vibration'),
        ('temperature', 'Temperature Extremes'),
        ('radiation', 'Radiation'),
        ('vehicular', 'Vehicular/Traffic'),
        ('other', 'Other'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('REPORTED', 'Reported'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('UNDER_REVIEW', 'Under Review'),
        ('ACTION_ASSIGNED', 'Action Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    ]
    
    approval_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending Approval'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ],
        default='PENDING'
    )
    
    HAZARD_TYPE_CHOICES = [
        ('UA', 'Unsafe Act'),
        ('UC', 'Unsafe Condition'),
        ('NM', 'Near Miss')
    ]
    
    hazard_type = models.CharField(
        max_length=2,
        choices=HAZARD_TYPE_CHOICES,
        help_text="UA - Unsafe Act (behavior), UC - Unsafe Condition (environment)"
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazards_approved"
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    approved_remarks = models.TextField(blank=True)
    
    # Auto-generated Report Number: HAZ-PLANT_CODE-YYYYMMDD-XXX
    report_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    
    # Reporter Information
    reporter_name = models.CharField(max_length=200)
    reporter_email = models.EmailField()
    reporter_phone = models.CharField(max_length=10, blank=True)
    
    # Behalf Information (ForeignKey relationships)

    behalf_person_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Name of the person on whose behalf the report is made"
    )

    # This ForeignKey is no longer actively used by the form but is kept
    # to avoid data loss on existing records. New records will leave this null.
    behalf_person = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hazards_reported_on_behalf',
        help_text="Employee on whose behalf report is being made"
    )
    behalf_person_dept = models.ForeignKey(
        'organizations.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hazards_on_behalf',
        help_text="Department of person on whose behalf report is being made"
    )
    
    # Basic Hazard Information
    hazard_title = models.CharField(max_length=255)
    hazard_description = models.TextField(help_text="Detailed description of the hazard")
    immediate_action = models.TextField(blank=True)
    hazard_category = models.CharField(max_length=30, choices=HAZARD_CATEGORIES)
    incident_datetime = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when hazard was identified"
    )
    
    # Risk Assessment
    severity = models.CharField(
        max_length=20, 
        choices=SEVERITY_CHOICES, 
        help_text="Severity level of the hazard"
    )
    
    # Location Information (Using Plant/Zone/Location hierarchy)
    plant = models.ForeignKey(
        Plant, 
        on_delete=models.CASCADE, 
        related_name='hazards',
        help_text="Plant where hazard was identified"
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.CASCADE, 
        related_name='hazards', 
        null=True, 
        blank=True,
        help_text="Zone within the plant"
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        related_name='hazards',
        help_text="Specific location where hazard exists"
    )
    sublocation = models.ForeignKey(
        SubLocation,
        on_delete=models.SET_NULL,
        related_name='hazards',
        null=True,
        blank=True,
        help_text="Optional: Specific sub-location where hazard was observed"
    )
    location_details = models.TextField(blank=True, help_text="Additional location information")
    
    # GPS Coordinates (Optional)
    # gps_latitude = models.DecimalField(
    #     max_digits=10, 
    #     decimal_places=6, 
    #     null=True, 
    #     blank=True,
    #     help_text="GPS latitude coordinate"
    # )
    # gps_longitude = models.DecimalField(
    #     max_digits=10, 
    #     decimal_places=6, 
    #     null=True, 
    #     blank=True,
    #     help_text="GPS longitude coordinate"
    # )
    
    # Additional Information
    injury_status = models.CharField(
        max_length=10, 
        blank=True,
        help_text="Whether anyone was injured (yes/no)"
    )
    # immediate_action = models.TextField(
    #     blank=True,
    #     help_text="Immediate actions taken to address the hazard"
    # )
    witnesses = models.TextField(
        blank=True,
        help_text="Names and contact details of witnesses"
    )
    
    # System Information
    report_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when report was submitted"
    )   
    user_agent = models.TextField(blank=True, help_text="Browser user agent information")
    report_source = models.CharField(
        max_length=50, 
        default='web_portal',
        help_text="Source of the report (web_portal, mobile_app, etc.)"
    )
    
    # Reporting Information
    reported_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='hazards_reported',
        help_text="User who reported the hazard"
    )
    reported_date = models.DateTimeField(auto_now_add=True)
    
    # Assignment and Status
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hazards_assigned',
        help_text="User assigned to resolve the hazard"
    )
    status = models.CharField(
        max_length=30, 
        choices=STATUS_CHOICES, 
        default='REPORTED',
        db_index=True
    )
    
    # Corrective Actions
    corrective_action_plan = models.TextField(
        blank=True,
        help_text="Planned corrective actions to address the hazard"
    )
    action_deadline = models.DateField(
        null=True, 
        blank=True,
        help_text="Deadline for completing corrective actions"
    )
    action_completed_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when corrective actions were completed"
    )
    
    # Closure Information
    closure_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when hazard was closed"
    )
    closure_remarks = models.TextField(
        blank=True,
        help_text="Remarks about hazard closure"
    )
    
    forwarded_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='forwarded_hazards'
    )
    forwarded_from = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True, 
        related_name='forwarding_user'
    )
    forward_reason = models.TextField(blank=True)
    forward_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-incident_datetime', '-created_at']
        verbose_name = 'Hazard Report'
        verbose_name_plural = 'Hazard Reports'
        indexes = [
            models.Index(fields=['-incident_datetime']),
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['hazard_category']),
            models.Index(fields=['plant', 'location']),
        ]
    
    def __str__(self):
        return f"{self.report_number} - {self.hazard_title}"
    
    def save(self, *args, **kwargs):
        # Generate report number if not exists
        if not self.report_number:
            today = datetime.date.today()
            date_str = today.strftime('%Y%m%d')
            plant_code = self.plant.code if self.plant else 'XXX'
            
            # Get count of hazards for today at this plant
            count = Hazard.objects.filter(
                report_number__contains=f'HAZ-{plant_code}-{date_str}'
            ).count()
            
            self.report_number = f'HAZ-{plant_code}-{date_str}-{count + 1:03d}'
        
        super().save(*args, **kwargs)
        
    def update_status_from_action_items(self):
        """
        Updates the hazard's status based on the state of its action items.
        This logic respects final states (CLOSED, REJECTED) and the approval workflow.
        """
        # Do not automatically change the status if it's in a final state.
        if self.status in ['CLOSED', 'REJECTED']:
            return
        
        # ✅ NEW: Don't auto-update if still in pre-approval stages
        # Let the approval process handle the transition to post-approval statuses
        if self.status in ['REPORTED', 'PENDING_APPROVAL']:
            return

        action_items = self.action_items.all()
        total_items = action_items.count()
        new_status = self.status  # Default to the current status

        if total_items == 0:
            # If all action items have been removed, revert to APPROVED
            if self.status in ['ACTION_ASSIGNED', 'IN_PROGRESS', 'RESOLVED']:
                new_status = 'APPROVED'
        else:
            # Action items exist, so determine the status based on their progress.
            completed_items = action_items.filter(status='COMPLETED').count()
            in_progress_items = action_items.filter(status='IN_PROGRESS').count()
            overdue_items = action_items.filter(status='OVERDUE').count()

            if completed_items == total_items:
                # All action items are completed, so the hazard is resolved.
                new_status = 'RESOLVED'
            elif in_progress_items > 0 or overdue_items > 0:
                # If any action item is 'In Progress' or 'Overdue', the hazard is 'In Progress'.
                new_status = 'IN_PROGRESS'
            else:
                # If items exist but none are 'In Progress' (i.e., they are all 'PENDING'),
                # the status is 'Action Assigned'.
                new_status = 'ACTION_ASSIGNED'
        
        # To prevent recursion and unnecessary database writes, only save if the status has changed.
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])  
        
    @property
    def is_action_overdue(self):
        """Check if action is overdue"""
        if self.action_deadline and self.status not in ['RESOLVED', 'CLOSED']:
            return datetime.date.today() > self.action_deadline
        return False
    
    @property
    def days_since_reported(self):
        """Days since hazard was reported"""
        return (datetime.date.today() - self.incident_datetime.date()).days
    
    @property
    def severity_badge_class(self):
        """Return Bootstrap badge class based on severity"""
        severity_classes = {
            'low': 'badge-success',
            'medium': 'badge-warning',
            'high': 'badge-orange',
            'critical': 'badge-danger',
        }
        return severity_classes.get(self.severity, 'badge-secondary')
    
    @property
    def status_badge_class(self):
        # --- SUGGESTED UPDATE ---
        # Added 'ACTION_ASSIGNED' for better visual feedback in the UI.
        status_classes = {
            'REPORTED': 'badge-info',
            'UNDER_REVIEW': 'badge-primary',
            'ACTION_ASSIGNED': 'badge-warning', # <-- Updated
            'IN_PROGRESS': 'badge-info',
            'RESOLVED': 'badge-success',
            'CLOSED': 'badge-secondary',
            'REJECTED': 'badge-danger',
            'PENDING_APPROVAL': 'badge-light',
            'APPROVED': 'badge-primary'
        }
        return status_classes.get(self.status, 'badge-secondary')
    
    @property
    def category_icon(self):
        """Return FontAwesome icon class for hazard category"""
        category_icons = {
            'slip_trip_fall': 'fa-person-falling',
            'chemical': 'fa-flask',
            'electrical': 'fa-bolt',
            'fire': 'fa-fire',
            'equipment': 'fa-cogs',
            'ergonomic': 'fa-chair',
            'biological': 'fa-biohazard',
            'environmental': 'fa-leaf',
            'confined_space': 'fa-box',
            'working_at_height': 'fa-person-climbing',
            'manual_handling': 'fa-box-open',
            'noise': 'fa-volume-up',
            'temperature': 'fa-temperature-high',
            'radiation': 'fa-radiation',
            'vehicular': 'fa-car',
            'other': 'fa-question-circle',
        }
        return category_icons.get(self.hazard_category, 'fa-exclamation-triangle')
    
    def get_full_location(self):
        """Get full location string"""
        parts = [self.plant.name]
        if self.zone:
            parts.append(self.zone.name)
        parts.append(self.location.name)
        if self.sublocation:
            parts.append(self.sublocation.name)
        return ' → '.join(parts)


class HazardPhoto(models.Model):
    """Photos related to hazard"""
    PHOTO_TYPE_CHOICES = [
        ('evidence', 'Evidence'),
        ('corrective_action', 'Corrective Action'),
        ('before', 'Before'),
        ('after', 'After'),
    ]
    
    hazard = models.ForeignKey(
        Hazard, 
        on_delete=models.CASCADE, 
        related_name='photos'
    )
    photo = models.ImageField(
        upload_to='hazard_photos/%Y/%m/',
        help_text="Hazard photo (max 5MB)"
    )
    photo_type = models.CharField(
        max_length=20,
        choices=PHOTO_TYPE_CHOICES,
        default='evidence',
        blank=True
    )
    description = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Brief description of the photo"
    )
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        help_text="User who uploaded the photo"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Hazard Photo'
        verbose_name_plural = 'Hazard Photos'
    
    def __str__(self):
        return f"{self.hazard.report_number} - Photo {self.id}"


class HazardActionItem(models.Model):
    """Action items for hazard resolution"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
    ]
    
    hazard = models.ForeignKey(
        Hazard, 
        on_delete=models.CASCADE, 
        related_name='action_items'
    )
    action_description = models.TextField(
        help_text="Description of the action to be taken"
    )
    
    # Email addresses (comma-separated)
    responsible_emails = models.TextField(
        blank=True,
        help_text="Email addresses of responsible persons (comma-separated)"
    )
    
    # NEW: Attachment field
    attachment = models.FileField(
        upload_to='action_item_attachments/%Y/%m/',
        help_text="Required file attachment (documents, images, etc.)"
    )
    
    target_date = models.DateField(
        help_text="Target date for completing the action"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING',
        db_index=True
    )
    completion_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when action was completed"
    )
    completion_remarks = models.TextField(
        blank=True,
        help_text="Remarks about action completion"
    )
    
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hazard_actions_verified',
        help_text="User who verified the action completion"
    )
    verification_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when action was verified"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['target_date', '-created_at']
        verbose_name = 'Hazard Action Item'
        verbose_name_plural = 'Hazard Action Items'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['target_date']),
        ]
    
    def __str__(self):
        return f"{self.hazard.report_number} - Action Item {self.id}"
    
    def get_emails_list(self):
        """Return list of emails"""
        if self.responsible_emails:
            return [email.strip() for email in self.responsible_emails.split(',') if email.strip()]
        return []
    
    def get_emails_count(self):
        """Return count of emails"""
        return len(self.get_emails_list())
    
    def get_attachment_name(self):
        """Get filename from attachment"""
        if self.attachment:
            import os
            return os.path.basename(self.attachment.name)
        return None
    
    def get_attachment_size(self):
        """Get attachment file size in human readable format"""
        if self.attachment:
            size = self.attachment.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
        return None
    
    @property
    def is_overdue(self):
        """Check if action item is overdue"""
        if self.status != 'COMPLETED' and self.target_date:
            return datetime.date.today() > self.target_date
        return False
    
    @property
    def days_until_deadline(self):
        """Calculate days until deadline"""
        if self.target_date and self.status != 'COMPLETED':
            delta = self.target_date - datetime.date.today()
            return delta.days
        return None
    
    @property
    def status_badge_class(self):
        """Return Bootstrap badge class based on status"""
        status_classes = {
            'PENDING': 'badge-warning',
            'IN_PROGRESS': 'badge-info',
            'COMPLETED': 'badge-success',
            'OVERDUE': 'badge-danger',
        }
        return status_classes.get(self.status, 'badge-secondary')
    
    def save(self, *args, **kwargs):
        # Auto-update status to OVERDUE if past target date
        if self.status not in ['COMPLETED', 'OVERDUE'] and self.target_date:
            if datetime.date.today() > self.target_date:
                self.status = 'OVERDUE'
        
        # Set completion date if status is COMPLETED and not already set
        if self.status == 'COMPLETED' and not self.completion_date:
            self.completion_date = datetime.date.today()
        
        super().save(*args, **kwargs)

class HazardNotification(models.Model):

    NOTIFICATION_TYPES = [
        ('HAZARD_REPORTED','Hazard Reported'),
        ('HAZARD_DUE','Hazard Due Soon'),
        ('HAZARD_OVERDUE','Hazard Overdue'),
        ('ACTION_ASSIGNED','Action Item Assigned'),
        ('ACTION_DUE','Action Item Due Soon'),
        ('HAZARD_CLOSED','Hazard Closed'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hazard_notifications'
    )
    hazard = models.ForeignKey(
        Hazard,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notifications_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient','is_read']),
            models.Index(fields=['-created_at']),
        ] 

    def __str__(self):
        return f"{self.recipient.get_full_name()} - {self.title}"
    
    def mark_as_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = timezone.now()
            self.save(update_fields=['is_read','read_at'])
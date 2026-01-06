# apps/inspections/models.py

from django.db import models
from django.conf import settings
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import json


class InspectionTemplate(models.Model):
    """Master template for different types of inspections (Fire Safety, Electrical, etc.)"""
    
    FREQUENCY_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('HALF_YEARLY', 'Half-Yearly'),
        ('YEARLY', 'Yearly'),
    ]
    
    template_name = models.CharField(max_length=200, verbose_name="Template Name")
    template_code = models.CharField(max_length=50, unique=True, verbose_name="Template Code")
    description = models.TextField(blank=True, verbose_name="Description")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='MONTHLY')
    document_number = models.CharField(max_length=100, blank=True, verbose_name="Document Number")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['template_name']
        verbose_name = 'Inspection Template'
        verbose_name_plural = 'Inspection Templates'
    
    def __str__(self):
        return f"{self.template_name} ({self.template_code})"
    
    def clean(self):
        if self.template_code:
            self.template_code = self.template_code.upper()
    
    @property
    def category_count(self):
        return self.categories.count()
    
    @property
    def total_inspection_points(self):
        return InspectionPoint.objects.filter(category__template=self).count()


class InspectionCategory(models.Model):
    """Categories within an inspection template (e.g., General Fire Safety, Production Hall)"""
    
    template = models.ForeignKey(InspectionTemplate, on_delete=models.CASCADE, related_name='categories')
    category_name = models.CharField(max_length=200, verbose_name="Category Name")
    sequence_order = models.IntegerField(default=0, verbose_name="Sequence Order")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['template', 'sequence_order', 'category_name']
        unique_together = ['template', 'category_name']
        verbose_name = 'Inspection Category'
        verbose_name_plural = 'Inspection Categories'
    
    def __str__(self):
        return f"{self.template.template_name} - {self.category_name}"
    
    @property
    def inspection_point_count(self):
        return self.inspection_points.count()


class InspectionPoint(models.Model):
    """Individual checklist items within a category"""
    
    category = models.ForeignKey(InspectionCategory, on_delete=models.CASCADE, related_name='inspection_points')
    inspection_point_text = models.TextField(verbose_name="Inspection Point")
    sequence_order = models.IntegerField(default=0, verbose_name="Sequence Order")
    is_mandatory = models.BooleanField(default=True, verbose_name="Is Mandatory")
    requires_photo = models.BooleanField(default=False, verbose_name="Requires Photo Evidence")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'sequence_order']
        verbose_name = 'Inspection Point'
        verbose_name_plural = 'Inspection Points'
    
    def __str__(self):
        return f"{self.category.category_name} - {self.inspection_point_text[:50]}"


class InspectionSchedule(models.Model):
    """Schedule for assigning inspections to HODs/Users"""
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    template = models.ForeignKey(InspectionTemplate, on_delete=models.CASCADE, related_name='schedules')
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='inspection_schedules')
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspection_schedules')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspection_schedules')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_inspections', 
                                    verbose_name="Assigned To (HOD)")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='scheduled_inspections',
                                   verbose_name="Assigned By (Safety Officer)")
    scheduled_date = models.DateField(verbose_name="Scheduled Date")
    due_date = models.DateField(verbose_name="Due Date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    notes = models.TextField(blank=True, verbose_name="Assignment Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-due_date']
        verbose_name = 'Inspection Schedule'
        verbose_name_plural = 'Inspection Schedules'
    
    def __str__(self):
        return f"{self.template.template_name} - {self.plant.name} - Due: {self.due_date}"
    
    def save(self, *args, **kwargs):
        # Auto-update status based on due date and completion
        if self.status not in ['COMPLETED', 'CANCELLED']:
            if timezone.now().date() > self.due_date:
                self.status = 'OVERDUE'
            elif hasattr(self, 'inspection') and self.inspection:
                self.status = 'IN_PROGRESS'
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        return self.status != 'COMPLETED' and timezone.now().date() > self.due_date
    
    @property
    def days_until_due(self):
        delta = self.due_date - timezone.now().date()
        return delta.days


class Inspection(models.Model):
    """Main inspection record when HOD conducts the inspection"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    inspection_schedule = models.OneToOneField(InspectionSchedule, on_delete=models.CASCADE, related_name='inspection', null=True, blank=True)
    inspection_number = models.CharField(max_length=100, unique=True, verbose_name="Inspection Number")
    template = models.ForeignKey(InspectionTemplate, on_delete=models.CASCADE, related_name='inspections')
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='inspections')
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
    
    conducted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conducted_inspections',
                                    verbose_name="Conducted By (HOD)")
    inspection_date = models.DateField(verbose_name="Inspection Date")
    month = models.CharField(max_length=20, blank=True, verbose_name="Month")
    year = models.IntegerField(blank=True, null=True, verbose_name="Year")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Compliance Score (%)")
    total_findings = models.IntegerField(default=0, verbose_name="Total Findings")
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='reviewed_inspections')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True, verbose_name="Review Comments")
    
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_inspections')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    pdf_report = models.FileField(upload_to='inspections/reports/%Y/%m/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-inspection_date']
        verbose_name = 'Inspection'
        verbose_name_plural = 'Inspections'
    
    def __str__(self):
        return f"{self.inspection_number} - {self.template.template_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate inspection number
        if not self.inspection_number:
            self.inspection_number = self.generate_inspection_number()
        
        # Auto-set month and year
        if self.inspection_date:
            self.month = self.inspection_date.strftime('%B')
            self.year = self.inspection_date.year
        
        super().save(*args, **kwargs)
    
    def generate_inspection_number(self):
        """Generate inspection number: LOC/TEMPLATE/YYYY/001"""
        year = timezone.now().year
        plant_code = self.plant.code if self.plant else 'NA'
        template_code = self.template.template_code if self.template else 'INSP'
        
        # Get last number for this plant/template/year
        last_inspection = Inspection.objects.filter(
            plant=self.plant,
            template=self.template,
            year=year
        ).order_by('-id').first()
        
        if last_inspection and last_inspection.inspection_number:
            try:
                last_num = int(last_inspection.inspection_number.split('/')[-1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        return f"{plant_code}/{template_code}/{year}/{new_num:03d}"
    
    def calculate_compliance_score(self):
        """Calculate compliance percentage based on Yes/No/NA responses"""
        responses = self.responses.all()
        if not responses:
            return 0
        
        total_responses = responses.count()
        yes_count = responses.filter(response='YES').count()
        na_count = responses.filter(response='NA').count()
        
        # Score = (Yes / (Total - NA)) * 100
        denominator = total_responses - na_count
        if denominator == 0:
            return 0
        
        score = (yes_count / denominator) * 100
        return round(score, 2)
    
    def update_findings_count(self):
        """Update total findings count"""
        self.total_findings = self.findings.count()
        self.save(update_fields=['total_findings'])


class InspectionResponse(models.Model):
    """Responses for each inspection point (Yes/No/NA with remarks)"""
    
    RESPONSE_CHOICES = [
        ('YES', 'Yes'),
        ('NO', 'No'),
        ('NA', 'N/A'),
    ]
    
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='responses')
    inspection_point = models.ForeignKey(InspectionPoint, on_delete=models.CASCADE, related_name='responses')
    category = models.ForeignKey(InspectionCategory, on_delete=models.CASCADE, related_name='responses')
    
    response = models.CharField(max_length=10, choices=RESPONSE_CHOICES, verbose_name="Response")
    remarks = models.TextField(blank=True, verbose_name="Remarks / Action Required")
    
    photo_1 = models.ImageField(upload_to='inspections/photos/%Y/%m/', null=True, blank=True)
    photo_2 = models.ImageField(upload_to='inspections/photos/%Y/%m/', null=True, blank=True)
    photo_3 = models.ImageField(upload_to='inspections/photos/%Y/%m/', null=True, blank=True)
    
    sequence_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['inspection', 'sequence_order']
        unique_together = ['inspection', 'inspection_point']
        verbose_name = 'Inspection Response'
        verbose_name_plural = 'Inspection Responses'
    
    def __str__(self):
        return f"{self.inspection.inspection_number} - {self.inspection_point.inspection_point_text[:30]} - {self.response}"
    
    def save(self, *args, **kwargs):
        # Auto-generate finding if response is "NO"
        is_new = self.pk is None
        old_response = None
        
        if not is_new:
            try:
                old_response = InspectionResponse.objects.get(pk=self.pk).response
            except InspectionResponse.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Create finding if response changed to NO or is NO for new response
        if self.response == 'NO':
            if is_new or (old_response and old_response != 'NO'):
                self.create_finding()
        # Delete finding if response changed from NO to something else
        elif old_response == 'NO' and self.response != 'NO':
            InspectionFinding.objects.filter(inspection_response=self).delete()
    
    def create_finding(self):
        """Auto-create finding when response is NO"""
        # Check if finding already exists
        if InspectionFinding.objects.filter(inspection_response=self).exists():
            return
        
        finding = InspectionFinding.objects.create(
            inspection=self.inspection,
            inspection_response=self,
            inspection_point_text=self.inspection_point.inspection_point_text,
            category_name=self.category.category_name,
            remarks=self.remarks,
            severity='MEDIUM',  # Default severity
            status='OPEN',
            assigned_to=self.inspection.plant.users.filter(role='SAFETY_MANAGER').first()  # Assign to safety officer
        )
        
        # Update inspection findings count
        self.inspection.update_findings_count()
        
        return finding


class InspectionFinding(models.Model):
    """Auto-generated findings when inspection response is 'No'"""
    
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical (7 days)'),
        ('HIGH', 'High (15 days)'),
        ('MEDIUM', 'Medium (30 days)'),
        ('LOW', 'Low (45 days)'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('UNDER_REVIEW', 'Under Review'),
        ('CLOSED', 'Closed'),
        ('REJECTED', 'Rejected'),
    ]
    
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='findings')
    inspection_response = models.OneToOneField(InspectionResponse, on_delete=models.CASCADE, related_name='finding', null=True, blank=True)
    finding_number = models.CharField(max_length=100, unique=True, verbose_name="Finding Number")
    
    inspection_point_text = models.TextField(verbose_name="Inspection Point")
    category_name = models.CharField(max_length=200, verbose_name="Category")
    remarks = models.TextField(verbose_name="Finding Remarks")
    
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM')
    
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='assigned_findings', verbose_name="Assigned To (Responsible Person)")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='findings_assigned', verbose_name="Assigned By (Safety Officer)")
    
    target_date = models.DateField(verbose_name="Target Date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    action_taken_description = models.TextField(blank=True, verbose_name="Action Taken Description")
    action_taken_photo_1 = models.ImageField(upload_to='inspections/findings/%Y/%m/', null=True, blank=True)
    action_taken_photo_2 = models.ImageField(upload_to='inspections/findings/%Y/%m/', null=True, blank=True)
    action_taken_photo_3 = models.ImageField(upload_to='inspections/findings/%Y/%m/', null=True, blank=True)
    
    closure_date = models.DateField(null=True, blank=True, verbose_name="Closure Date")
    closure_remarks = models.TextField(blank=True, verbose_name="Closure Remarks")
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='closed_findings')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inspection Finding'
        verbose_name_plural = 'Inspection Findings'
    
    def __str__(self):
        return f"{self.finding_number} - {self.inspection_point_text[:50]}"
    
    def save(self, *args, **kwargs):
        # Auto-generate finding number
        if not self.finding_number:
            self.finding_number = self.generate_finding_number()
        
        # Auto-calculate target date based on severity
        if not self.target_date:
            self.target_date = self.calculate_target_date()
        
        super().save(*args, **kwargs)
    
    def generate_finding_number(self):
        """Generate finding number: LOC/FIND/YYYY/001"""
        year = timezone.now().year
        plant_code = self.inspection.plant.code if self.inspection.plant else 'NA'
        
        # Get last number for this plant/year
        last_finding = InspectionFinding.objects.filter(
            inspection__plant=self.inspection.plant,
            created_at__year=year
        ).order_by('-id').first()
        
        if last_finding and last_finding.finding_number:
            try:
                last_num = int(last_finding.finding_number.split('/')[-1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        return f"{plant_code}/FIND/{year}/{new_num:03d}"
    
    def calculate_target_date(self):
        """Calculate target date based on severity"""
        days_map = {
            'CRITICAL': 7,
            'HIGH': 15,
            'MEDIUM': 30,
            'LOW': 45,
        }
        days = days_map.get(self.severity, 30)
        return timezone.now().date() + timedelta(days=days)
    
    @property
    def is_overdue(self):
        return self.status != 'CLOSED' and timezone.now().date() > self.target_date
    
    @property
    def days_until_due(self):
        if self.status == 'CLOSED':
            return 0
        delta = self.target_date - timezone.now().date()
        return delta.days


class InspectionAttachment(models.Model):
    """Additional attachments for inspections and findings"""
    
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    finding = models.ForeignKey(InspectionFinding, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    
    file = models.FileField(upload_to='inspections/attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.IntegerField(blank=True, null=True, help_text="File size in bytes")
    
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Inspection Attachment'
        verbose_name_plural = 'Inspection Attachments'
    
    def __str__(self):
        return f"{self.file_name}"
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.name
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
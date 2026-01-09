from django.db import models

# Create your models here.
# apps/data_collection/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
import json

User = get_user_model()


class DataCollectionCategory(models.Model):
    """Main categories for data collection (e.g., Waste Management, Energy, Emissions)"""
    
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=50, default='fas fa-folder', 
                                   help_text='Font Awesome icon class')
    display_order = models.IntegerField(default=0, help_text='Order in which to display')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Data Collection Category'
        verbose_name_plural = 'Data Collection Categories'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        if self.code:
            self.code = self.code.upper()
    
    @property
    def question_count(self):
        return self.questions.count()
    
    @property
    def active_question_count(self):
        return self.questions.filter(is_active=True).count()


class DataCollectionQuestion(models.Model):
    """Individual questions/parameters within categories"""
    
    FIELD_TYPE_CHOICES = [
        ('NUMBER', 'Number/Numeric'),
        ('TEXT', 'Text/Short Answer'),
        ('TEXTAREA', 'Long Text/Paragraph'),
        ('DROPDOWN', 'Dropdown/Select'),
        ('CHECKBOX', 'Checkbox (Yes/No)'),
        ('RADIO', 'Radio Button'),
        ('FILE', 'File Upload'),
        ('DATE', 'Date'),
        ('EMAIL', 'Email'),
    ]
    
    category = models.ForeignKey(DataCollectionCategory, on_delete=models.CASCADE, 
                                  related_name='questions')
    question_text = models.CharField(max_length=500)
    question_code = models.CharField(max_length=100, 
                                      help_text='Unique code for this question')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='NUMBER')
    help_text = models.CharField(max_length=500, blank=True, 
                                  help_text='Additional guidance for user')
    placeholder = models.CharField(max_length=200, blank=True)
    
    # Field-specific options
    unit_of_measurement = models.CharField(max_length=50, blank=True, 
                                            help_text='e.g., kg, liters, kWh, tons')
    options_json = models.TextField(blank=True, 
                                     help_text='JSON array of options for dropdown/radio fields')
    
    # Validation rules
    is_required = models.BooleanField(default=False)
    min_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                     help_text='Minimum value for numeric fields')
    max_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                     help_text='Maximum value for numeric fields')
    min_length = models.IntegerField(null=True, blank=True,
                                      help_text='Minimum characters for text fields')
    max_length = models.IntegerField(null=True, blank=True,
                                      help_text='Maximum characters for text fields')
    
    # Display settings
    display_order = models.IntegerField(default=0)
    show_on_summary = models.BooleanField(default=True, 
                                          help_text='Show this in summary reports')
    
    # Assignment settings
    applicable_to_all_plants = models.BooleanField(default=True)
    applicable_plants = models.ManyToManyField(Plant, blank=True, 
                                                related_name='applicable_questions',
                                                help_text='Leave empty for all plants')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'display_order', 'question_text']
        unique_together = ['category', 'question_code']
        verbose_name = 'Data Collection Question'
        verbose_name_plural = 'Data Collection Questions'
    
    def __str__(self):
        return f"{self.category.code} - {self.question_text}"
    
    def clean(self):
        if self.question_code:
            self.question_code = self.question_code.upper()
        
        # Validate options_json
        if self.options_json:
            try:
                options = json.loads(self.options_json)
                if not isinstance(options, list):
                    raise ValidationError({'options_json': 'Must be a JSON array'})
            except json.JSONDecodeError:
                raise ValidationError({'options_json': 'Invalid JSON format'})
        
        # Validate numeric constraints
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValidationError('Minimum value cannot be greater than maximum value')
    
    def get_options_list(self):
        """Parse and return options as list"""
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except json.JSONDecodeError:
                return []
        return []


class DataCollectionPeriod(models.Model):
    """Represents a data collection period (e.g., January 2025)"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
        ('ARCHIVED', 'Archived'),
    ]
    
    name = models.CharField(max_length=200, help_text='e.g., "January 2025"')
    year = models.IntegerField()
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    start_date = models.DateField()
    end_date = models.DateField()
    submission_deadline = models.DateField(help_text='Last date to submit data')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    description = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                    related_name='created_periods')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['year', 'month']
        verbose_name = 'Data Collection Period'
        verbose_name_plural = 'Data Collection Periods'
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError('Start date cannot be after end date')
        
        if self.submission_deadline and self.end_date:
            if self.submission_deadline < self.end_date:
                raise ValidationError('Submission deadline should be on or after end date')
    
    @property
    def is_active(self):
        return self.status == 'ACTIVE'
    
    @property
    def is_overdue(self):
        if self.submission_deadline:
            return timezone.now().date() > self.submission_deadline
        return False
    
    @property
    def days_remaining(self):
        if self.submission_deadline:
            delta = self.submission_deadline - timezone.now().date()
            return delta.days
        return None


class MonthlyDataCollection(models.Model):
    """Main container for monthly data collection by location"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    period = models.ForeignKey(DataCollectionPeriod, on_delete=models.CASCADE, 
                                related_name='collections')
    
    # Location hierarchy
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='data_collections')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='data_collections')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, 
                                  related_name='data_collections')
    sublocation = models.ForeignKey(SubLocation, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='data_collections')
    
    # Optional department
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='data_collections')
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # User tracking
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name='reported_collections')
    reported_at = models.DateTimeField(auto_now_add=True)
    
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='submitted_collections')
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reviewed_collections')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='approved_collections')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_comments = models.TextField(blank=True)
    
    # Additional info
    remarks = models.TextField(blank=True, help_text='General remarks or notes')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-period__year', '-period__month', 'plant', 'location']
        unique_together = ['period', 'plant', 'location']
        verbose_name = 'Monthly Data Collection'
        verbose_name_plural = 'Monthly Data Collections'
        indexes = [
            models.Index(fields=['period', 'plant', 'status']),
            models.Index(fields=['status', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.period.name} - {self.plant.name} - {self.location.name}"
    
    def clean(self):
        # Validate location hierarchy
        if self.zone and self.zone.plant != self.plant:
            raise ValidationError('Zone must belong to the selected plant')
        
        if self.location and self.location.zone.plant != self.plant:
            raise ValidationError('Location must belong to the selected plant')
        
        if self.sublocation and self.sublocation.location != self.location:
            raise ValidationError('Sub-location must belong to the selected location')
    
    @property
    def completion_percentage(self):
        """Calculate percentage of required questions answered"""
        total_required = DataCollectionQuestion.objects.filter(
            is_active=True,
            is_required=True,
            category__is_active=True
        ).count()
        
        if total_required == 0:
            return 100
        
        answered = self.responses.filter(
            question__is_required=True
        ).exclude(
            models.Q(numeric_value__isnull=True) & 
            models.Q(text_value='') & 
            models.Q(file_value='')
        ).count()
        
        return int((answered / total_required) * 100)
    
    @property
    def is_complete(self):
        """Check if all required questions are answered"""
        return self.completion_percentage == 100
    
    @property
    def can_submit(self):
        """Check if collection can be submitted"""
        return self.status == 'DRAFT' and self.is_complete
    
    @property
    def can_approve(self):
        """Check if collection can be approved"""
        return self.status in ['SUBMITTED', 'UNDER_REVIEW']
    
    def submit(self, user):
        """Submit the collection"""
        if not self.can_submit:
            raise ValidationError('Collection cannot be submitted')
        
        self.status = 'SUBMITTED'
        self.submitted_by = user
        self.submitted_at = timezone.now()
        self.save()
    
    def review(self, user, comments=''):
        """Mark as under review"""
        if self.status != 'SUBMITTED':
            raise ValidationError('Only submitted collections can be reviewed')
        
        self.status = 'UNDER_REVIEW'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_comments = comments
        self.save()
    
    def approve(self, user, comments=''):
        """Approve the collection"""
        if not self.can_approve:
            raise ValidationError('Collection cannot be approved')
        
        self.status = 'APPROVED'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.approval_comments = comments
        self.save()
    
    def reject(self, user, comments):
        """Reject the collection"""
        if not self.can_approve:
            raise ValidationError('Collection cannot be rejected')
        
        self.status = 'REJECTED'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_comments = comments
        self.save()


class DataCollectionResponse(models.Model):
    """Individual responses to questions"""
    
    collection = models.ForeignKey(MonthlyDataCollection, on_delete=models.CASCADE,
                                    related_name='responses')
    question = models.ForeignKey(DataCollectionQuestion, on_delete=models.CASCADE,
                                  related_name='responses')
    
    # Multiple value fields to support different field types
    numeric_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    text_value = models.TextField(blank=True)
    date_value = models.DateField(null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    file_value = models.FileField(upload_to='data_collection_files/%Y/%m/', null=True, blank=True)
    
    # For storing selected option (dropdown/radio)
    selected_option = models.CharField(max_length=200, blank=True)
    
    # Metadata
    unit_used = models.CharField(max_length=50, blank=True, 
                                  help_text='Unit of measurement used for this response')
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['collection', 'question__category', 'question__display_order']
        unique_together = ['collection', 'question']
        verbose_name = 'Data Collection Response'
        verbose_name_plural = 'Data Collection Responses'
    
    def __str__(self):
        return f"{self.collection} - {self.question.question_code}"
    
    def clean(self):
        # Validate based on question field type
        field_type = self.question.field_type
        
        if field_type == 'NUMBER' and self.numeric_value is not None:
            if self.question.min_value is not None and self.numeric_value < self.question.min_value:
                raise ValidationError(f'Value must be at least {self.question.min_value}')
            if self.question.max_value is not None and self.numeric_value > self.question.max_value:
                raise ValidationError(f'Value must be at most {self.question.max_value}')
        
        if field_type in ['TEXT', 'TEXTAREA'] and self.text_value:
            if self.question.min_length and len(self.text_value) < self.question.min_length:
                raise ValidationError(f'Text must be at least {self.question.min_length} characters')
            if self.question.max_length and len(self.text_value) > self.question.max_length:
                raise ValidationError(f'Text must be at most {self.question.max_length} characters')
        
        # Validate required fields
        if self.question.is_required:
            if field_type == 'NUMBER' and self.numeric_value is None:
                raise ValidationError('This numeric field is required')
            elif field_type in ['TEXT', 'TEXTAREA', 'EMAIL'] and not self.text_value:
                raise ValidationError('This text field is required')
            elif field_type == 'DATE' and not self.date_value:
                raise ValidationError('This date field is required')
            elif field_type == 'CHECKBOX' and self.boolean_value is None:
                raise ValidationError('This checkbox field is required')
            elif field_type == 'FILE' and not self.file_value:
                raise ValidationError('File upload is required')
            elif field_type in ['DROPDOWN', 'RADIO'] and not self.selected_option:
                raise ValidationError('Please select an option')
    
    def get_display_value(self):
        """Get formatted display value based on field type"""
        field_type = self.question.field_type
        
        if field_type == 'NUMBER':
            if self.numeric_value is not None:
                unit = self.unit_used or self.question.unit_of_measurement
                if unit:
                    return f"{self.numeric_value} {unit}"
                return str(self.numeric_value)
        elif field_type in ['TEXT', 'TEXTAREA', 'EMAIL']:
            return self.text_value
        elif field_type == 'DATE':
            return self.date_value.strftime('%d/%m/%Y') if self.date_value else ''
        elif field_type == 'CHECKBOX':
            return 'Yes' if self.boolean_value else 'No'
        elif field_type in ['DROPDOWN', 'RADIO']:
            return self.selected_option
        elif field_type == 'FILE':
            return self.file_value.name if self.file_value else ''
        
        return 'N/A'


class DataCollectionAttachment(models.Model):
    """Additional file attachments for data collection"""
    
    collection = models.ForeignKey(MonthlyDataCollection, on_delete=models.CASCADE,
                                    related_name='attachments')
    file = models.FileField(upload_to='data_collection_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    file_size = models.IntegerField(help_text='File size in bytes')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Data Collection Attachment'
        verbose_name_plural = 'Data Collection Attachments'
    
    def __str__(self):
        return f"{self.collection} - {self.filename}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            if not self.filename:
                self.filename = self.file.name
        super().save(*args, **kwargs)


class DataCollectionComment(models.Model):
    """Comments/Notes on data collections"""
    
    collection = models.ForeignKey(MonthlyDataCollection, on_delete=models.CASCADE,
                                    related_name='comments')
    comment = models.TextField()
    commented_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    commented_at = models.DateTimeField(auto_now_add=True)
    is_internal = models.BooleanField(default=False, 
                                       help_text='Internal comments not visible to reporters')
    
    class Meta:
        ordering = ['-commented_at']
        verbose_name = 'Data Collection Comment'
        verbose_name_plural = 'Data Collection Comments'
    
    def __str__(self):
        return f"Comment on {self.collection} by {self.commented_by}"


class DataCollectionAssignment(models.Model):
    """Assign data collection responsibility to users"""
    
    period = models.ForeignKey(DataCollectionPeriod, on_delete=models.CASCADE,
                                related_name='assignments')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='data_collection_assignments')
    
    # Location assignment
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    sublocation = models.ForeignKey(SubLocation, on_delete=models.CASCADE, null=True, blank=True)
    
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name='assigned_data_collections')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    notification_sent = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-assigned_at']
        unique_together = ['period', 'assigned_to', 'location']
        verbose_name = 'Data Collection Assignment'
        verbose_name_plural = 'Data Collection Assignments'
    
    def __str__(self):
        return f"{self.period} - {self.assigned_to.get_full_name()} - {self.location}"
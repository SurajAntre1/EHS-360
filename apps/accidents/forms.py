from django import forms
from django.core.exceptions import ValidationError
from .models import *
from datetime import date
from .models import Incident, IncidentType
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from django.core.validators import validate_email
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class IncidentTypeForm(forms.ModelForm):
    class Meta:
        model = IncidentType
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Lost Time Injury'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., LTI',
                'maxlength': '20'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description...'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})


class IncidentReportForm(forms.ModelForm):
    """Form for creating/updating incident reports with manual affected person entry"""
    
    # ===== MANUAL AFFECTED PERSON FIELDS =====
    
    # Employment Category
    affected_employment_category = forms.ChoiceField(
        choices=[
            ('', '-- Select Employment Category --'),
            ('PERMANENT', 'Permanent'),
            ('CONTRACT', 'Contract'),
            ('ON_ROLL', 'On Roll'),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        error_messages={
            'required': 'Please select an employment category.'
        }
    )
    
    # Name
    affected_person_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter full name'
        }),
        error_messages={
            'required': 'Please enter the name of the affected person.'
        }
    )
    
    # Employee ID
    affected_person_employee_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter employee ID'
        }),
        error_messages={
            'required': 'Please enter the employee ID.'
        }
    )
    
    # Department - From Master Table
    affected_person_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True).order_by('name'),
        required=True,
        empty_label='-- Select Department --',
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        error_messages={
            'required': 'Please select a department.',
            'invalid_choice': 'Please select a valid department from the list.'
        }
    )
    
    # Date of Birth
    affected_date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        error_messages={
            'required': 'Please enter the date of birth.',
            'invalid': 'Please enter a valid date.'
        }
    )
    
    # Age (Auto-calculated, read-only)
    affected_age = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control readonly-field',
            'placeholder': 'Calculated automatically',
            'readonly': 'readonly'
        })
    )
    
    # Gender
    affected_gender = forms.ChoiceField(
        choices=[
            ('', '-- Select Gender --'),
            ('MALE', 'Male'),
            ('FEMALE', 'Female'),
            ('OTHER', 'Other'),
            ('PREFER_NOT_TO_SAY', 'Prefer not to say'),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
        }),
        error_messages={
            'required': 'Please select a gender.'
        }
    )
    
    # Job Title
    affected_job_title = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter job title'
        }),
        error_messages={
            'required': 'Please enter the job title.'
        }
    )
    
    # Date of Joining
    affected_date_of_joining = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        error_messages={
            'required': 'Please enter the date of joining.',
            'invalid': 'Please enter a valid date.'
        }
    )
    
    class Meta:
        model = Incident
        fields = [
            'incident_type',
            'incident_date', 
            'incident_time',
            'plant', 
            'zone', 
            'location', 
            'sublocation',
            'additional_location_details',
            'description',
            # Affected person fields
            'affected_employment_category',
            'affected_person_name', 
            'affected_person_employee_id', 
            'affected_person_department',
            'affected_date_of_birth',
            'affected_age',
            'affected_gender',
            'affected_job_title',
            'affected_date_of_joining',
            'nature_of_injury',
        ]
        
        widgets = {
            'incident_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'incident_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'incident_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
            'plant': forms.Select(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'sublocation': forms.Select(attrs={'class': 'form-control'}),
            'additional_location_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Specific area, equipment, or landmark near the hazard'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Describe what happened in detail, sequence of events, and circumstances'
            }),
            'nature_of_injury': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Describe the type and extent of injury (e.g., cut, fracture, burn)'
            }),
        }
        
        error_messages = {
            'incident_type': {
                'required': 'Please select an incident type.'
            },
            'incident_date': {
                'required': 'Please enter the incident date.',
                'invalid': 'Please enter a valid date.'
            },
            'incident_time': {
                'required': 'Please enter the incident time.',
                'invalid': 'Please enter a valid time.'
            },
            'plant': {
                'required': 'Please select a plant.'
            },
            'location': {
                'required': 'Please select a location.'
            },
            'description': {
                'required': 'Please provide a detailed description of the incident.'
            },
            'nature_of_injury': {
                'required': 'Please describe the nature of injury.'
            }
        }

    def __init__(self, *args, **kwargs):
        """
        Dynamically adjusts form fields for both Create and Update views,
        and correctly populates querysets during POST requests for validation.
        """
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set empty labels
        self.fields['plant'].empty_label = "Select Plant"
        self.fields['zone'].empty_label = "Select Zone"
        self.fields['location'].empty_label = "Select Location"
        self.fields['sublocation'].empty_label = "Select sub-location"
        
        # ✅ POPULATE incident_type dropdown with active types from database
        self.fields['incident_type'].queryset = IncidentType.objects.filter(is_active=True).order_by('name')
        self.fields['incident_type'].label_from_instance = lambda obj: f"{obj.code} - {obj.name}"
        self.fields['incident_type'].empty_label = "Select incident type"
        
        # Base queryset for the top-level field (Plant) based on user permissions.
        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.exists():
                self.fields['plant'].queryset = assigned_plants
            else:
                self.fields['plant'].queryset = Plant.objects.filter(is_active=True)
        else:
            self.fields['plant'].queryset = Plant.objects.filter(is_active=True)

        # Handle POST data for cascading dropdowns
        if self.data:
            try:
                plant_id = int(self.data.get('plant'))
                self.fields['zone'].queryset = Zone.objects.filter(plant_id=plant_id, is_active=True).order_by('name')
                
                zone_id = int(self.data.get('zone'))
                self.fields['location'].queryset = Location.objects.filter(zone_id=zone_id, is_active=True).order_by('name')
                
                location_id = int(self.data.get('location'))
                self.fields['sublocation'].queryset = SubLocation.objects.filter(location_id=location_id, is_active=True).order_by('name')
            except (ValueError, TypeError):
                pass
        
        # Handle editing existing instance
        elif self.instance and self.instance.pk:
            if self.instance.plant:
                self.fields['zone'].queryset = Zone.objects.filter(plant=self.instance.plant, is_active=True).order_by('name')
            if self.instance.zone:
                self.fields['location'].queryset = Location.objects.filter(zone=self.instance.zone, is_active=True).order_by('name')
            if self.instance.location:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(location=self.instance.location, is_active=True).order_by('name')

        # Handle creating new instance (pre-fill logic)
        elif self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.count() == 1:
                plant = assigned_plants.first()
                self.initial['plant'] = plant.pk
                
                assigned_zones = self.user.assigned_zones.filter(plant=plant, is_active=True)
                self.fields['zone'].queryset = assigned_zones
                
                if assigned_zones.count() == 1:
                    zone = assigned_zones.first()
                    self.initial['zone'] = zone.pk
                    
                    assigned_locations = self.user.assigned_locations.filter(zone=zone, is_active=True)
                    self.fields['location'].queryset = assigned_locations
                    
                    if assigned_locations.count() == 1:
                        location = assigned_locations.first()
                        self.initial['location'] = location.pk
                        
                        assigned_sublocations = self.user.assigned_sublocations.filter(location=location, is_active=True)
                        self.fields['sublocation'].queryset = assigned_sublocations
                        
                        if assigned_sublocations.count() == 1:
                            self.initial['sublocation'] = assigned_sublocations.first().pk
                                                             
    def clean_affected_date_of_birth(self):
        """Validate date of birth"""
        dob = self.cleaned_data.get('affected_date_of_birth')
        
        if dob:
            today = date.today()
            
            if dob > today:
                raise ValidationError("Date of birth cannot be in the future.")
            
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if age < 16:
                raise ValidationError(
                    f"The affected person must be at least 16 years old. "
                    f"Current age based on date of birth: {age} years."
                )
            
            if age > 100:
                raise ValidationError(
                    f"Please verify the date of birth. The calculated age is {age} years, which seems incorrect."
                )
        
        return dob
    
    def clean_affected_date_of_joining(self):
        """Validate date of joining"""
        doj = self.cleaned_data.get('affected_date_of_joining')
        
        if doj:
            today = date.today()
            
            if doj > today:
                raise ValidationError("Date of joining cannot be in the future.")
        
        return doj
    
    def clean_incident_date(self):
        """Validate incident date"""
        incident_date = self.cleaned_data.get('incident_date')
        
        if incident_date:
            today = date.today()
            
            if incident_date > today:
                raise ValidationError("Incident date cannot be in the future.")
        
        return incident_date
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        dob = cleaned_data.get('affected_date_of_birth')
        doj = cleaned_data.get('affected_date_of_joining')
        
        if dob and doj:
            if doj <= dob:
                raise ValidationError({
                    'affected_date_of_joining': "Date of joining must be after the date of birth."
                })
            
            age_at_joining = doj.year - dob.year - ((doj.month, doj.day) < (dob.month, dob.day))
            
            if age_at_joining < 16:
                raise ValidationError({
                    'affected_date_of_joining': f"Person must be at least 16 years old at the time of joining. Age at joining: {age_at_joining} years."
                })
        
        return cleaned_data


class IncidentUpdateForm(forms.ModelForm):
    """Form for updating existing incidents"""
    
    class Meta:
        model = Incident
        fields = [
            'incident_type', 'incident_date', 'incident_time',
            'plant', 'zone', 'location', 'sublocation',
            'description',
            'affected_person_name', 'affected_person_employee_id', 'affected_person_department',
            'nature_of_injury',
            'status',
        ]
        
        widgets = {
            'incident_type': forms.Select(attrs={'class': 'form-control'}),
            'incident_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'incident_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'plant': forms.Select(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'sublocation': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'affected_person_name': forms.TextInput(attrs={'class': 'form-control'}),
            'affected_person_employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'affected_person_department': forms.Select(attrs={'class': 'form-control'}),
            'nature_of_injury': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # ✅ POPULATE incident_type dropdown
        incident_type_qs = IncidentType.objects.filter(is_active=True)
        if self.instance.pk and self.instance.incident_type:
            incident_type_qs = incident_type_qs | IncidentType.objects.filter(pk=self.instance.incident_type.pk)
        self.fields['incident_type'].queryset = incident_type_qs.distinct().order_by('name')
        self.fields['incident_type'].label_from_instance = lambda obj: f"{obj.code} - {obj.name}"
        self.fields['incident_type'].empty_label = "Select incident type"


class IncidentInvestigationReportForm(forms.ModelForm):
    """Form for investigation reports"""

    investigation_team = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter email(s), separated by commas. e.g. user1@example.com, user2@example.com'
            }
        )
    )

    class Meta:
        model = IncidentInvestigationReport
        fields = [
            'investigation_date', 'investigation_team',
            'sequence_of_events', 'root_cause_analysis', 
            'personal_factors', 'job_factors',
            'evidence_collected', 'witness_statements',
            'immediate_corrective_actions', 'preventive_measures', 
            'completed_date',
        ]

        widgets = {
            'investigation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sequence_of_events': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'root_cause_analysis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'evidence_collected': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'witness_statements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'immediate_corrective_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preventive_measures': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'completed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }


# Custom form field to display user's full name and email.
class UserChoiceField(forms.ModelMultipleChoiceField):
    """
    Custom field to display user choices as 'Full Name (email)'.
    """
    def label_from_instance(self, obj):
        # This method controls how each user object is displayed in the dropdown.
        full_name = obj.get_full_name()
        if full_name and full_name.strip():
            return f"{full_name} ({obj.email})"
        return obj.email # Fallback to email if full name is not available.


class IncidentActionItemForm(forms.ModelForm):
    """
    Form for action items, with dynamic assignment type logic.
    """
    responsible_person = UserChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-responsible-person',
            'data-placeholder': 'Search and select person(s)...'
        }),
        required=False, 
        label="Responsible Person(s)"
    )

    assignment_type = forms.ChoiceField(
        choices=IncidentActionItem.ASSIGNMENT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='SELF',
        required=True
    )

    
    # completion_date ko form me explicitly 'required=False' set karein.
    completion_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    # --------------------------------

    class Meta:
        model = IncidentActionItem
        fields = [
            'action_description',
            'assignment_type',
            'responsible_person',
            'target_date',
            'completion_date', 
            'attachment',
            'status',
        ]
        widgets = {
            'action_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'target_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control-file'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize the form, setting the queryset for responsible persons
        based on the incident's plant.
        """
        incident = kwargs.pop('incident', None)
        super().__init__(*args, **kwargs)

        # Populate responsible_person queryset based on the incident's plant.
        if incident and incident.plant:
            self.fields['responsible_person'].queryset = User.objects.filter(
                assigned_plants=incident.plant,
                is_active=True,
                is_active_employee=True
            ).distinct().order_by('first_name', 'last_name')
        else:
            self.fields['responsible_person'].queryset = User.objects.none()

    def clean_target_date(self):
        target_date = self.cleaned_data.get('target_date')
        if target_date and target_date < timezone.now().date():
            raise ValidationError("Target date cannot be in the past.")
        return target_date

    def clean(self):
        # Server-side validation based on assignment type.
        cleaned_data = super().clean()
        assignment_type = cleaned_data.get('assignment_type')
        responsible_person = cleaned_data.get('responsible_person')
        attachment = cleaned_data.get('attachment')

        if assignment_type == 'FORWARD' and not responsible_person:
            self.add_error('responsible_person', 'This field is required when forwarding to others.')

        if assignment_type == 'SELF' and not attachment:
            # Check if an instance exists (i.e., this is an update)
            if not self.instance or not self.instance.attachment:
                 self.add_error('attachment', 'An attachment is required for self-assignment and immediate closure.')
        
        return cleaned_data
    

class IncidentPhotoForm(forms.ModelForm):
    """Form for incident photos"""
    
    class Meta:
        model = IncidentPhoto
        fields = ['photo', 'photo_type', 'description']
        
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control-file'}),
            'photo_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }


class IncidentClosureForm(forms.ModelForm):
    """Form for closing an incident"""
    
    class Meta:
        model = Incident
        fields = [
            'closure_remarks',
            'lessons_learned',
            'preventive_measures',
            'is_recurrence_possible'
        ]
        widgets = {
            'closure_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide final closure remarks...'
            }),
            'lessons_learned': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'What did we learn from this incident?'
            }),
            'preventive_measures': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'What measures have been implemented to prevent recurrence?'
            }),
            'is_recurrence_possible': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class IncidentAttachmentForm(forms.ModelForm):
    """
    A simple form dedicated to uploading the closure attachment on the
    verification screen.
    """
    class Meta:
        model = Incident
        fields = ['attachment']
        widgets = {
            'attachment': forms.FileInput(attrs={'class': 'form-control-file'})
        }
        error_messages = {
            'attachment': {
                'required': 'Please select a file to upload. This field is required.'
            }
        }
        
        
class IncidentActionItemCompleteForm(forms.ModelForm):
    """
    Form for users to complete an action item with remarks and an attachment.
    """
    class Meta:
        model = IncidentActionItem
        fields = [
            'completion_date',
            'completion_remarks',
            'attachment'
        ]
        widgets = { 
            'completion_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control bg-light', 'readonly': 'readonly'}
            ),
            'completion_remarks': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe what actions were taken...'}
            ),
            'attachment': forms.FileInput(
                attrs={'class': 'form-control-file'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure Remarks are required
        self.fields['completion_remarks'].required = True
        
        # MODIFIED: Make attachment required and update label
        self.fields['attachment'].required = True 
        self.fields['attachment'].label = "Upload Proof/Attachment"
        
        # Set today's date as the initial value for completion_date
        self.fields['completion_date'].initial = timezone.now().date()


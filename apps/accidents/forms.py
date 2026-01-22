from django import forms
from django.core.exceptions import ValidationError
from .models import *
from datetime import date
 
# from django.contrib.auth.models import User
from .models import Incident
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department
from apps.organizations.models import *

class IncidentReportForm(forms.ModelForm):
    """Form for creating/updating incident reports with manual affected person entry"""
    
    # Updated incident_type to include FATALITY and exclude Near Miss
    incident_type = forms.ChoiceField(
        choices=[
            ('', 'Select incident type'),
            ('FA', 'First Aid (FA)'),
            ('MTC', 'Medical Treatment Case (MTC/RWC)'),
            ('LTI', 'Lost Time Injury (LTI)'),
            ('HLFI', 'High Lost Frequency Injury (HLFI)'),
            ('FATALITY', 'Fatality'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
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
        self.fields['plant'].empty_label = "Select Plant"
        self.fields['zone'].empty_label = "Select Zone"
        self.fields['location'].empty_label = "Select Location"
        self.fields['sublocation'].empty_label = "Select sub-location"

        # Base queryset for the top-level field (Plant) based on user permissions.
        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            if assigned_plants.exists():
                self.fields['plant'].queryset = assigned_plants
            else: # Fallback for users (like admins) with no specific assignments
                self.fields['plant'].queryset = Plant.objects.filter(is_active=True)
        else: # Fallback if user is somehow not available
            self.fields['plant'].queryset = Plant.objects.filter(is_active=True)

        # self.data contains the POST data. If it exists, it means the form is being submitted.
        # We MUST populate the querysets based on the submitted data for validation to pass.
        if self.data:
            try:
                plant_id = int(self.data.get('plant'))
                self.fields['zone'].queryset = Zone.objects.filter(plant_id=plant_id, is_active=True).order_by('name')
                
                zone_id = int(self.data.get('zone'))
                self.fields['location'].queryset = Location.objects.filter(zone_id=zone_id, is_active=True).order_by('name')
                
                location_id = int(self.data.get('location'))
                self.fields['sublocation'].queryset = SubLocation.objects.filter(location_id=location_id, is_active=True).order_by('name')
            except (ValueError, TypeError):
                # This can happen if a field is not submitted. We pass silently
                # as the form's own validation will catch the required field error.
                pass
        
        # If not a POST request, handle the initial display for GET requests.
        elif self.instance and self.instance.pk: # Editing an existing instance
            if self.instance.plant:
                self.fields['zone'].queryset = Zone.objects.filter(plant=self.instance.plant, is_active=True).order_by('name')
            if self.instance.zone:
                self.fields['location'].queryset = Location.objects.filter(zone=self.instance.zone, is_active=True).order_by('name')
            if self.instance.location:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(location=self.instance.location, is_active=True).order_by('name')

        elif self.user: # Creating a new instance (pre-fill logic)
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
            
            # Check if DOB is not in future
            if dob > today:
                raise ValidationError("Date of birth cannot be in the future.")
            
            # Calculate age
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            # Check minimum age
            if age < 16:
                raise ValidationError(
                    f"The affected person must be at least 16 years old. "
                    f"Current age based on date of birth: {age} years."
                )
            
            # Check maximum age
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
            
            # Check if DOJ is not in future
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
        
        # Get dates
        dob = cleaned_data.get('affected_date_of_birth')
        doj = cleaned_data.get('affected_date_of_joining')
        
        # Validate DOJ is after DOB
        if dob and doj:
            if doj <= dob:
                raise ValidationError({
                    'affected_date_of_joining': "Date of joining must be after the date of birth."
                })
            
            # Calculate age at joining
            age_at_joining = doj.year - dob.year - ((doj.month, doj.day) < (dob.month, dob.day))
            
            if age_at_joining < 16:
                raise ValidationError({
                    'affected_date_of_joining': f"Person must be at least 16 years old at the time of joining. Age at joining: {age_at_joining} years."
                })
        
        return cleaned_data


class IncidentUpdateForm(forms.ModelForm):
    """Form for updating existing incidents"""
    
    incident_type = forms.ChoiceField(
        choices=[
            ('', 'Select incident type'),
            ('FA', 'First Aid (FA)'),
            ('MTC', 'Medical Treatment Case (MTC/RWC)'),
            ('LTI', 'Lost Time Injury (LTI)'),
            ('HLFI', 'High Lost Frequency Injury (HLFI)'),
            ('FATALITY', 'Fatality'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
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


class IncidentInvestigationReportForm(forms.ModelForm):
    """Form for investigation reports"""
    
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
            'investigation_team': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'sequence_of_events': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'root_cause_analysis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # 'contributing_factors': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # 'unsafe_conditions_identified': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            # 'unsafe_acts_identified': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'evidence_collected': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'witness_statements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'immediate_corrective_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preventive_measures': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'completed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

####
class IncidentActionItemForm(forms.ModelForm):
    """Form for action items with email validation."""

    responsible_person_emails = forms.CharField(
        label="Responsible Person (Email Addresses)",
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Type email and press Enter or comma...'
        })
    )

    class Meta:
        model = IncidentActionItem
        fields = [
            'action_description',
            'target_date',
            'status',
            'completion_date',
        ]

        widgets = {
            'action_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'target_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'completion_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean_responsible_person_emails(self):
        """
        Custom validation to ensure all provided emails belong to existing users.
        """
        emails_string = self.cleaned_data.get('responsible_person_emails', '')
        if not emails_string:
            return '' # required=True will handle the empty case

        # Split emails, strip whitespace, and convert to lowercase for case-insensitive check
        email_list = [email.strip().lower() for email in emails_string.split(',') if email.strip()]
        
        # Remove duplicates
        unique_emails = list(set(email_list))
        
        if not unique_emails:
            raise forms.ValidationError("Please provide at least one valid email address.")

        # Query the database for users with these emails
        found_users = User.objects.filter(email__in=unique_emails)
        
        # Create a list of emails that were found in the database
        found_emails = [user.email.lower() for user in found_users]
        
        # Find which emails from the input were not found in the database
        missing_emails = [email for email in unique_emails if email not in found_emails]

        if missing_emails:
            # If any email is not found, raise a validation error with a clear message
            raise forms.ValidationError(
                f"The following users could not be found: {', '.join(missing_emails)}. "
                "Please ensure all email addresses are correct and belong to registered users."
            )
        
        # Return the original, cleaned string of emails for the view to process
        return emails_string
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
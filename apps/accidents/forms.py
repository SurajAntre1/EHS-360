from django import forms
from django.core.exceptions import ValidationError
from .models import *
from datetime import date

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
        super().__init__(*args, **kwargs)
        
        # Make zone and sublocation not required initially
        self.fields['zone'].required = False
        self.fields['sublocation'].required = False
        self.fields['location'].required = True
        
        # IMPORTANT: Allow empty sublocation value
        self.fields['sublocation'].empty_label = "-- Select Sub-Location --"
        
        # Make nature_of_injury required
        self.fields['nature_of_injury'].required = True
        
        # Set empty querysets for zone and location
        self.fields['zone'].queryset = Zone.objects.none()
        self.fields['location'].queryset = Location.objects.none()
        self.fields['sublocation'].queryset = SubLocation.objects.none()
        
        # If instance exists (editing), populate zone and location
        if self.instance.pk:
            if self.instance.plant:
                self.fields['zone'].queryset = Zone.objects.filter(
                    plant=self.instance.plant, is_active=True
                )
            if self.instance.zone:
                self.fields['location'].queryset = Location.objects.filter(
                    zone=self.instance.zone, is_active=True
                )
            if self.instance.location:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location=self.instance.location, is_active=True
                )
    
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
            'sequence_of_events', 'root_cause_analysis', 'contributing_factors',
            'unsafe_conditions_identified', 'unsafe_acts_identified',
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
            'contributing_factors': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'unsafe_conditions_identified': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'unsafe_acts_identified': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'evidence_collected': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'witness_statements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'immediate_corrective_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preventive_measures': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'completed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

####
class IncidentActionItemForm(forms.ModelForm):
    """Form for action items"""
    
    class Meta:
        model = IncidentActionItem
        fields = [
            'action_description', 'responsible_person', 'target_date',
            'status', 'completion_date', 'completion_remarks',
        ]
        
        widgets = {
            'action_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'responsible_person': forms.Select(attrs={'class': 'form-control'}),
            'target_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'completion_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


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
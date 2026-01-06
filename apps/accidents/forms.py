from django import forms
from .models import *

class IncidentReportForm(forms.ModelForm):
    """Form for creating/updating incident reports"""
    
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
    
    class Meta:
        model = Incident
        fields = [
            'incident_type', 'incident_date', 'incident_time',
            'plant', 'zone', 'location', 'sublocation',
            'description',
            'affected_person_name', 'affected_person_employee_id', 'affected_person_department',
            'nature_of_injury',
        ]
        
        widgets = {
            'incident_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'incident_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'plant': forms.Select(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'sublocation': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Describe what happened in detail, sequence of events, and circumstances'
            }),
            'affected_person_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Full name', 
                'readonly': 'readonly'
            }),
            'affected_person_employee_id': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Employee ID', 
                'readonly': 'readonly'
            }),
            'affected_person_department': forms.Select(attrs={'class': 'form-control'}),
            'nature_of_injury': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2, 
                'placeholder': 'Describe the type and extent of injury (e.g., cut, fracture, burn)'
            }),
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
        from apps.organizations.models import Zone, Location, SubLocation
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
        # ===== MODIFIED SECTION START =====
        # Removed 'action_items' and 'target_completion_date' from the fields list.
        fields = [
            'investigation_date', 'investigation_team',
            'sequence_of_events', 'root_cause_analysis', 'contributing_factors',
            'unsafe_conditions_identified', 'unsafe_acts_identified',
            'personal_factors', 'job_factors',
            'evidence_collected', 'witness_statements',
            'immediate_corrective_actions', 'preventive_measures', 
            'completed_date',
        ]
        # ===== MODIFIED SECTION END =====
        
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
            # ===== MODIFIED SECTION START =====
            # Removed widgets for the deleted fields.
            # 'action_items': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            # 'target_completion_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            # ===== MODIFIED SECTION END =====
            'completed_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

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
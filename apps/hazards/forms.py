from django import forms
from django.contrib.auth import get_user_model
from .models import Hazard, HazardActionItem, HazardPhoto
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department

User = get_user_model()


class HazardForm(forms.ModelForm):
    """
    Form for creating and updating hazard reports
    Supports both single and multiple hazard submissions
    """
    
    class Meta:
        model = Hazard
        fields = [
            'hazard_type',
            'hazard_category',
            'severity',
            'plant',
            'zone',
            'location',
            'sublocation',
            'location_details',
            'hazard_description',
            'immediate_action',
            'incident_datetime',
            'behalf_person_name',
            'behalf_person_dept',
        ]
        
        widgets = {
            'plant': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_plant'
            }),
            'zone': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_zone'
            }),
            'location': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_location'
            }),
            'sublocation': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_sublocation'
            }),
            'hazard_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'hazard_category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'severity': forms.Select(attrs={
                'class': 'form-control'
            }),
            'hazard_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the hazard in detail...'
            }),
            'immediate_action': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe immediate actions taken...'
            }),
            'location_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional location details...'
            }),
            'incident_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'behalf_person_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter employee name'
            }),
            'behalf_person_dept': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter querysets based on user's assigned locations
        if self.user:
            # Plant filtering
            if self.user.assigned_plants.exists():
                self.fields['plant'].queryset = self.user.assigned_plants.filter(is_active=True)
            elif self.user.plant:
                self.fields['plant'].queryset = Plant.objects.filter(id=self.user.plant.id, is_active=True)
            else:
                self.fields['plant'].queryset = Plant.objects.filter(is_active=True)
            
            # Zone filtering
            if self.user.assigned_zones.exists():
                self.fields['zone'].queryset = self.user.assigned_zones.filter(is_active=True)
            elif self.user.zone:
                self.fields['zone'].queryset = Zone.objects.filter(id=self.user.zone.id, is_active=True)
            else:
                self.fields['zone'].queryset = Zone.objects.filter(is_active=True)
            
            # Location filtering
            if self.user.assigned_locations.exists():
                self.fields['location'].queryset = self.user.assigned_locations.filter(is_active=True)
            elif self.user.location:
                self.fields['location'].queryset = Location.objects.filter(id=self.user.location.id, is_active=True)
            else:
                self.fields['location'].queryset = Location.objects.filter(is_active=True)
            
            # Sublocation filtering
            if self.user.assigned_sublocations.exists():
                self.fields['sublocation'].queryset = self.user.assigned_sublocations.filter(is_active=True)
            elif self.user.sublocation:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(id=self.user.sublocation.id, is_active=True)
            else:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(is_active=True)
        
        # Make zone and sublocation optional
        self.fields['zone'].required = False
        self.fields['sublocation'].required = False
        self.fields['location_details'].required = False
        self.fields['immediate_action'].required = False
        self.fields['behalf_person_name'].required = False
        self.fields['behalf_person_dept'].required = False
        
        # Set empty labels for dropdowns
        self.fields['plant'].empty_label = "-- Select Plant --"
        self.fields['zone'].empty_label = "-- Select Zone --"
        self.fields['location'].empty_label = "-- Select Location --"
        self.fields['sublocation'].empty_label = "-- Select Sub-Location --"
        self.fields['behalf_person_dept'].empty_label = "-- Select Department --"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate location hierarchy
        plant = cleaned_data.get('plant')
        zone = cleaned_data.get('zone')
        location = cleaned_data.get('location')
        sublocation = cleaned_data.get('sublocation')
        
        if zone and zone.plant != plant:
            raise forms.ValidationError('Selected zone does not belong to the selected plant.')
        
        if location and location.zone != zone:
            raise forms.ValidationError('Selected location does not belong to the selected zone.')
        
        if sublocation and sublocation.location != location:
            raise forms.ValidationError('Selected sub-location does not belong to the selected location.')
        
        return cleaned_data


class HazardActionItemForm(forms.ModelForm):
    """
    Form for creating and updating hazard action items
    Supports both self-assignment and forwarding to team members
    """
    
    # Additional field for multiple user selection
    responsible_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Assign to Team Members"
    )
    
    assignment_type = forms.ChoiceField(
        choices=[
            ('self', 'Self-Assign & Complete'),
            ('forward', 'Forward to Team'),
        ],
        initial='forward',
        widget=forms.RadioSelect,
        label="Assignment Type"
    )
    
    class Meta:
        model = HazardActionItem
        fields = [
            'action_description',
            'target_date',
            'attachment',
        ]
        
        widgets = {
            'action_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the corrective action to be taken...'
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.hazard = kwargs.pop('hazard', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set up the responsible_users queryset based on hazard's plant
        if self.hazard and self.hazard.plant:
            from django.db.models import Q
            
            self.fields['responsible_users'].queryset = User.objects.filter(
                Q(plant=self.hazard.plant) | Q(assigned_plants=self.hazard.plant),
                is_active=True,
                is_active_employee=True
            ).exclude(
                id=self.user.id if self.user else None
            ).distinct().select_related('department', 'role').order_by('first_name', 'last_name')
        
        # Add help text
        self.fields['action_description'].help_text = "Provide a detailed description of the corrective action"
        self.fields['target_date'].help_text = "Deadline for completing this action"
        self.fields['attachment'].help_text = "Upload supporting documents or images (Required)"
        
        # Make attachment required
        self.fields['attachment'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        assignment_type = cleaned_data.get('assignment_type')
        responsible_users = cleaned_data.get('responsible_users')
        
        # If forwarding, ensure at least one user is selected
        if assignment_type == 'forward':
            if not responsible_users or len(responsible_users) == 0:
                raise forms.ValidationError(
                    'Please select at least one team member when forwarding the action item.'
                )
        
        return cleaned_data


class HazardPhotoForm(forms.ModelForm):
    """
    Form for uploading hazard photos
    """
    
    class Meta:
        model = HazardPhoto
        fields = ['photo', 'photo_type', 'description']
        
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
            'photo_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the photo'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['photo_type'].required = False
        self.fields['description'].required = False


class HazardFilterForm(forms.Form):
    """
    Form for filtering hazards in list view
    """
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by report number or title...'
        })
    )
    
    hazard_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + list(Hazard.HAZARD_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    risk_level = forms.ChoiceField(
        required=False,
        choices=[('', 'All Severities')] + list(Hazard.SEVERITY_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(Hazard.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    approval_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Approval Statuses'),
            ('PENDING', 'Pending Approval'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class HazardApprovalForm(forms.Form):
    """
    Form for approving or rejecting hazards
    """
    
    action = forms.ChoiceField(
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
        ],
        widget=forms.RadioSelect,
        label="Decision"
    )
    
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add remarks (required for rejection)...'
        }),
        label="Remarks"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        remarks = cleaned_data.get('remarks')
        
        # Remarks are required when rejecting
        if action == 'reject' and not remarks:
            raise forms.ValidationError('Remarks are required when rejecting a hazard report.')
        
        return cleaned_data
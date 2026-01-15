# apps/inspections/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    InspectionTemplate, InspectionCategory, InspectionPoint,
    InspectionSchedule, Inspection, InspectionResponse, InspectionFinding
)
from apps.organizations.models import Plant, Zone, Location, Department
from apps.accounts.models import User,Role


class InspectionScheduleForm(forms.ModelForm):
    """Form for Safety Officers to schedule/assign inspections"""
    
    class Meta:
        model = InspectionSchedule
        fields = [
            'template', 'plant', 'zone', 'location', 
            'assigned_to', 'scheduled_date', 'due_date', 'notes'
        ]
        widgets = {
            'template': forms.Select(attrs={
                'class': 'form-control select2',
                'required': True
            }),
            'plant': forms.Select(attrs={
                'class': 'form-control select2',
                'required': True
            }),
            'zone': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'location': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control select2',
                'required': True
            }),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any special instructions or notes for the inspector...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter templates to show only active ones
        self.fields['template'].queryset = InspectionTemplate.objects.filter(is_active=True)
        
        # If user has a plant assigned, filter accordingly
        if self.user and self.user.plant:
            self.fields['plant'].queryset = Plant.objects.filter(id=self.user.plant.id)
            self.fields['plant'].initial = self.user.plant
            
            # Filter zones for user's plant
            self.fields['zone'].queryset = Zone.objects.filter(plant=self.user.plant, is_active=True)
            
            # Filter locations for user's plant
            self.fields['location'].queryset = Location.objects.filter(zone__plant=self.user.plant, is_active=True)
            
            # Filter assigned_to to HODs in the same plant
            self.fields['assigned_to'].queryset = User.objects.filter(
                plant=self.user.plant,
                role__name='HOD',
                is_active=True
            )
        else:
            # Superuser can see all
            self.fields['plant'].queryset = Plant.objects.filter(is_active=True)
            self.fields['zone'].queryset = Zone.objects.filter(is_active=True)
            self.fields['location'].queryset = Location.objects.filter(is_active=True)
            self.fields['assigned_to'].queryset = User.objects.filter(role__name='HOD', is_active=True)
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_date = cleaned_data.get('scheduled_date')
        due_date = cleaned_data.get('due_date')
        
        if scheduled_date and due_date:
            if due_date < scheduled_date:
                raise ValidationError({
                    'due_date': 'Due date cannot be before scheduled date.'
                })
        
        return cleaned_data


class InspectionForm(forms.ModelForm):
    """Form for conducting inspections"""
    
    class Meta:
        model = Inspection
        fields = ['inspection_date', 'department']
        widgets = {
            'inspection_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'department': forms.Select(attrs={
                'class': 'form-control select2'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.template = kwargs.pop('template', None)
        super().__init__(*args, **kwargs)
        
        # Filter departments
        if self.user and self.user.plant:
            self.fields['department'].queryset = Department.objects.filter(is_active=True)
        
        # Set initial department from user
        if self.user and self.user.department:
            self.fields['department'].initial = self.user.department


class InspectionResponseForm(forms.ModelForm):
    """Form for individual inspection point responses"""
    
    class Meta:
        model = InspectionResponse
        fields = ['response', 'remarks', 'photo_1', 'photo_2', 'photo_3']
        widgets = {
            'response': forms.RadioSelect(attrs={
                'class': 'response-input'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Please describe the issue and action required...'
            }),
            'photo_1': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
            'photo_2': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
            'photo_3': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
        }


class FindingAssignmentForm(forms.ModelForm):
    """Form for Safety Officers to assign findings"""
    
    class Meta:
        model = InspectionFinding
        fields = ['assigned_to', 'severity', 'target_date', 'remarks']
        widgets = {
            'assigned_to': forms.Select(attrs={
                'class': 'form-control select2',
                'required': True
            }),
            'severity': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional instructions or remarks...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to users based on plant
        if self.user and self.user.plant:
            self.fields['assigned_to'].queryset = User.objects.filter(
                plant=self.user.plant,
                is_active=True
            ).exclude(role__name='EMPLOYEE')
        else:
            self.fields['assigned_to'].queryset = User.objects.filter(
                is_active=True
            ).exclude(role__name='EMPLOYEE')


class FindingActionForm(forms.ModelForm):
    """Form for responsible persons to update action taken on findings"""
    
    class Meta:
        model = InspectionFinding
        fields = [
            'action_taken_description',
            'action_taken_photo_1',
            'action_taken_photo_2',
            'action_taken_photo_3'
        ]
        widgets = {
            'action_taken_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the corrective action taken in detail...',
                'required': True
            }),
            'action_taken_photo_1': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
            'action_taken_photo_2': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
            'action_taken_photo_3': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
        }
    
    def clean_action_taken_description(self):
        description = self.cleaned_data.get('action_taken_description')
        if not description or len(description.strip()) < 20:
            raise ValidationError('Action description must be at least 20 characters long.')
        return description


class FindingClosureForm(forms.ModelForm):
    """Form for Safety Officers to close findings"""
    
    class Meta:
        model = InspectionFinding
        fields = ['closure_remarks']
        widgets = {
            'closure_remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Remarks on closure/verification...',
                'required': True
            }),
        }


class InspectionTemplateForm(forms.ModelForm):
    """Form for creating/editing inspection templates"""
    
    class Meta:
        model = InspectionTemplate
        fields = [
            'template_name', 'template_code', 'description',
            'frequency', 'document_number', 'is_active'
        ]
        widgets = {
            'template_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fire Safety Inspection',
                'required': True
            }),
            'template_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FSIC (will be auto-uppercased)',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Template description...'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'document_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., EIL/FSIC/EHS/F-01'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class InspectionCategoryForm(forms.ModelForm):
    """Form for creating/editing inspection categories"""
    
    class Meta:
        model = InspectionCategory
        fields = ['category_name', 'sequence_order', 'is_active']
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., General Fire Safety',
                'required': True
            }),
            'sequence_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class InspectionPointForm(forms.ModelForm):
    """Form for creating/editing inspection points"""
    
    class Meta:
        model = InspectionPoint
        fields = [
            'inspection_point_text', 'sequence_order',
            'is_mandatory', 'requires_photo', 'is_active'
        ]
        widgets = {
            'inspection_point_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'e.g., Fire extinguishers are available at designated locations.',
                'required': True
            }),
            'sequence_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            }),
            'is_mandatory': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_photo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class InspectionFilterForm(forms.Form):
    """Form for filtering inspection list"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
    ]
    
    plant = forms.ModelChoiceField(
        queryset=Plant.objects.filter(is_active=True),
        required=False,
        empty_label="All Plants",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    template = forms.ModelChoiceField(
        queryset=InspectionTemplate.objects.filter(is_active=True),
        required=False,
        empty_label="All Templates",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    month = forms.ChoiceField(
        choices=[('', 'All Months')] + [(str(i), str(i)) for i in range(1, 13)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    year = forms.ChoiceField(
        choices=[('', 'All Years')] + [(str(i), str(i)) for i in range(2024, 2031)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by inspection number...'
        })
    )


class FindingFilterForm(forms.Form):
    """Form for filtering findings list"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('UNDER_REVIEW', 'Under Review'),
        ('CLOSED', 'Closed'),
    ]
    
    SEVERITY_CHOICES = [
        ('', 'All Severities'),
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    
    plant = forms.ModelChoiceField(
        queryset=Plant.objects.filter(is_active=True),
        required=False,
        empty_label="All Plants",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    severity = forms.ChoiceField(
        choices=SEVERITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    assigned_to_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    overdue_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by finding number...'
        })
    )
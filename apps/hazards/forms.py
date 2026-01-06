from django import forms
from .models import Hazard, HazardPhoto, HazardActionItem
from apps.organizations.models import Plant, Zone, Location
from django.contrib.auth import get_user_model

User = get_user_model()


class HazardReportForm(forms.ModelForm):
    """Form for reporting new hazard"""
    
    class Meta:
        model = Hazard
        fields = [
            'hazard_category', 'hazard_title', 'hazard_description', 'incident_datetime',
            'severity', 'plant', 'zone', 'location', 'location_details',
            'injury_status', 'immediate_action', 'witnesses'
        ]
        widgets = {
            'hazard_category': forms.Select(attrs={'class': 'form-control', 'id': 'hazard_category'}),
            'hazard_title': forms.TextInput(attrs={
                'class': 'form-control', 
                'id': 'hazard_title',
                'placeholder': 'Title will be auto-generated...'
            }),
            'hazard_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'id': 'hazard_description',
                'rows': 4,
                'placeholder': 'Describe the hazard in detail...'
            }),
            'incident_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'id': 'incident_datetime'
            }),
            'severity': forms.Select(attrs={'class': 'form-control', 'id': 'severity'}),
            'plant': forms.Select(attrs={'class': 'form-control', 'id': 'plant'}),
            'zone': forms.Select(attrs={'class': 'form-control', 'id': 'zone'}),
            'location': forms.Select(attrs={'class': 'form-control', 'id': 'location'}),
            'location_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any additional location information...'
            }),
            'injury_status': forms.TextInput(attrs={'class': 'form-control'}),
            'immediate_action': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Area cordoned off, warning signs placed'
            }),
            'witnesses': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Names and contact details of witnesses...'
            }),
        }


class HazardUpdateForm(forms.ModelForm):
    """Form for updating hazard"""
    
    class Meta:
        model = Hazard
        fields = ['status', 'assigned_to', 'corrective_action_plan', 'action_deadline']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'corrective_action_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'action_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class HazardActionItemForm(forms.ModelForm):
    """Form for managing hazard action items"""
    
    class Meta:
        model = HazardActionItem
        fields = ['action_description', 'responsible_person', 'target_date', 'status', 'completion_date', 'completion_remarks']
        widgets = {
            'action_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'responsible_person': forms.Select(attrs={'class': 'form-control'}),
            'target_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completion_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class HazardPhotoForm(forms.ModelForm):
    """Form for uploading hazard photos"""
    
    class Meta:
        model = HazardPhoto
        fields = ['photo', 'description']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control-file'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Photo description'}),
        }
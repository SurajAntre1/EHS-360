from django import forms
from .models import Hazard, HazardPhoto, HazardActionItem
from apps.organizations.models import Plant, Zone, Location
from django.contrib.auth import get_user_model
from apps.organizations.models import Department, Plant, Zone, Location, SubLocation
from django.core.exceptions import ValidationError
from datetime import date

User = get_user_model()



class HazardForm(forms.ModelForm):
    """
    A unified ModelForm for creating and updating Hazard reports.
    It dynamically handles location fields based on user assignments.
    """
    class Meta:
        model = Hazard
        fields = [
            'reporter_name', 'incident_datetime',
            'plant', 'zone', 'location', 'sublocation', 'location_details',
            'behalf_person_name', 'behalf_person_dept',
            'hazard_type', 'hazard_category', 'severity',
            'hazard_description', 'immediate_action',
        ]
        widgets = {
            'incident_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'reporter_name': forms.TextInput(attrs={'class': 'form-control'}),
            'plant': forms.Select(attrs={'class': 'form-control'}),
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.Select(attrs={'class': 'form-control'}),
            'sublocation': forms.Select(attrs={'class': 'form-control'}),
            'location_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Specific area, equipment, or landmark...'}),
            'behalf_person_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Enter employee's full name"}),
            'behalf_person_dept': forms.Select(attrs={'class': 'form-control'}),
            'hazard_type': forms.Select(attrs={'class': 'form-control'}),
            'hazard_category': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'hazard_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe what you observed...'}),
            'immediate_action': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe any immediate steps taken...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['plant'].empty_label = "Select Plant"
        self.fields['zone'].empty_label = "Select Zone"
        self.fields['location'].empty_label = "Select Location"
        self.fields['sublocation'].empty_label = "Select sub-location"

        self.fields['behalf_person_dept'].queryset = Department.objects.filter(is_active=True).order_by('name')
        self.fields['behalf_person_dept'].required = False
        self.fields['behalf_person_name'].required = False
        self.fields['zone'].required = False
        self.fields['sublocation'].required = False
        
        # Initialize querysets to be empty
        self.fields['plant'].queryset = Plant.objects.none()
        self.fields['zone'].queryset = Zone.objects.none()
        self.fields['location'].queryset = Location.objects.none()
        self.fields['sublocation'].queryset = SubLocation.objects.none()

        if self.user:
            assigned_plants = self.user.assigned_plants.filter(is_active=True)
            self.fields['plant'].queryset = assigned_plants if assigned_plants.exists() else Plant.objects.filter(is_active=True)

        if self.data:
            try:
                plant_id = int(self.data.get('plant'))
                self.fields['zone'].queryset = Zone.objects.filter(plant_id=plant_id, is_active=True)
                zone_id = int(self.data.get('zone'))
                self.fields['location'].queryset = Location.objects.filter(zone_id=zone_id, is_active=True)
                location_id = int(self.data.get('location'))
                self.fields['sublocation'].queryset = SubLocation.objects.filter(location_id=location_id, is_active=True)
            except (ValueError, TypeError):
                pass
        
        elif self.instance and self.instance.pk: # Edit mode
            if self.instance.plant:
                self.fields['zone'].queryset = Zone.objects.filter(plant=self.instance.plant, is_active=True)
            if self.instance.zone:
                self.fields['location'].queryset = Location.objects.filter(zone=self.instance.zone, is_active=True)
            if self.instance.location:
                self.fields['sublocation'].queryset = SubLocation.objects.filter(location=self.instance.location, is_active=True)

        elif self.user: # Create mode
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
    
        fields = ['action_description', 'responsible_emails', 'target_date', 'status', 'completion_date', 'completion_remarks']
        widgets = {
            'action_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'responsible_emails': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Comma-separated emails'}), # Iska widget bhi set kar dein
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
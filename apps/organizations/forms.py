from django import forms
from .models import Plant, Zone, Location, Department


class PlantForm(forms.ModelForm):
    """Plant Form"""
    
    class Meta:
        model = Plant
        fields = ['name', 'code', 'address', 'city', 'state', 'pincode', 
                  'contact_person', 'contact_email', 'contact_phone', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Plant Name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Plant Code (e.g., EP001)'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Complete Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Contact Email'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Phone'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ZoneForm(forms.ModelForm):
    """Zone Form - Now includes ability to add multiple locations"""
    
    class Meta:
        model = Zone
        fields = ['plant', 'name', 'code', 'description', 'is_active']
        widgets = {
            'plant': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zone Name (e.g., Zone A, Zone B)'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zone Code (e.g., ZA, ZB)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LocationForm(forms.ModelForm):
    plant = forms.ModelChoiceField(
        queryset=Plant.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Plant --"
    )
    
    class Meta:
        model = Location
        fields = ['zone', 'name', 'code', 'description', 'is_active']
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Storage Area 1'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., L001'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing, set plant from zone
        if self.instance.pk and self.instance.zone:
            self.fields['plant'].initial = self.instance.zone.plant
            # Load zones for the plant
            self.fields['zone'].queryset = Zone.objects.filter(
                plant=self.instance.zone.plant, 
                is_active=True
            )
        else:
            # Empty zone queryset initially
            self.fields['zone'].queryset = Zone.objects.none()
        
        # Set zone to show "Select plant first" if no plant selected
        if 'plant' in self.data:
            try:
                plant_id = int(self.data.get('plant'))
                self.fields['zone'].queryset = Zone.objects.filter(
                    plant_id=plant_id, 
                    is_active=True
                ).order_by('name')
            except (ValueError, TypeError):
                pass


class DepartmentForm(forms.ModelForm):
    """Department Form"""
    
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'head_name', 'head_email', 'head_phone', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Code (e.g., SAFETY)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'head_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Head Name'}),
            'head_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Department Head Email'}),
            'head_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department Head Phone'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
# apps/inspections/forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    InspectionCategory,
    InspectionQuestion,
    InspectionTemplate,
    TemplateQuestion,
    InspectionSchedule
)
from apps.accounts.models import User
from apps.organizations.models import Plant, Zone, Location, SubLocation, Department


class InspectionCategoryForm(forms.ModelForm):
    class Meta:
        model = InspectionCategory
        fields = [
            'category_name',
            'category_code',
            'description',
            'icon',
            'display_order',
            'is_active'
        ]
        widgets = {
            'category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name (e.g., Fire Safety)'
            }),
            'category_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FS, ES, HK',
                'maxlength': '10'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this category'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'FontAwesome icon class (e.g., fa-fire)'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_category_code(self):
        code = self.cleaned_data.get('category_code')
        if code:
            code = code.upper()
            # Check if code already exists (excluding current instance)
            existing = InspectionCategory.objects.filter(category_code=code)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError(f'Category code "{code}" already exists.')
        return code


class InspectionQuestionForm(forms.ModelForm):
    class Meta:
        model = InspectionQuestion
        fields = [
            'category',
            'question_text',
            'question_type',
            'is_remarks_mandatory',
            'is_photo_required',
            'is_critical',
            'auto_generate_finding',
            'weightage',
            'display_order',
            'reference_standard',
            'guidance_notes',
            'is_active'
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter the inspection question'
            }),
            'question_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'weightage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01',
                'value': '1.00'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '0'
            }),
            'reference_standard': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., OSHA 1910.36, IS 2309'
            }),
            'guidance_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional guidance for inspectors'
            }),
            'is_remarks_mandatory': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_photo_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_critical': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'auto_generate_finding': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


# apps/inspections/forms.py

class InspectionTemplateForm(forms.ModelForm):
    class Meta:
        model = InspectionTemplate
        fields = [
            'template_name',
            # 'template_code',  # REMOVE THIS - auto-generated
            'inspection_type',
            'description',
            'applicable_plants',
            'applicable_departments',
            'requires_approval',
            'min_compliance_score',
            'is_active'
        ]
        widgets = {
            'template_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Monthly Plant Safety Inspection'
            }),
            'inspection_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the purpose of this inspection'
            }),
            'applicable_plants': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '5'
            }),
            'applicable_departments': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '5'
            }),
            'min_compliance_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01',
                'value': '80.00'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

class TemplateQuestionForm(forms.ModelForm):
    """Form for adding questions to a template"""
    
    class Meta:
        model = TemplateQuestion
        fields = [
            'question',
            'is_mandatory',
            'display_order',
            'section_name'
        ]
        widgets = {
            'question': forms.Select(attrs={
                'class': 'form-control select2'
            }),
            'is_mandatory': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'section_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional section name'
            })
        }


class BulkAddQuestionsForm(forms.Form):
    """Form for bulk adding questions to template"""
    
    category = forms.ModelChoiceField(
        queryset=InspectionCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'id_bulk_category'
        }),
        label="Filter by Category"
    )
    
    questions = forms.ModelMultipleChoiceField(
        queryset=InspectionQuestion.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select Questions"
    )
    
    section_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional section name for selected questions'
        }),
        label="Section Name (Optional)"
    )
    
    def __init__(self, *args, **kwargs):
        template = kwargs.pop('template', None)
        super().__init__(*args, **kwargs)
        
        if template:
            # Exclude questions already in template
            existing_question_ids = template.template_questions.values_list('question_id', flat=True)
            self.fields['questions'].queryset = InspectionQuestion.objects.filter(
                is_active=True
            ).exclude(id__in=existing_question_ids)


class InspectionScheduleForm(forms.ModelForm):
    class Meta:
        model = InspectionSchedule
        fields = [
            'template',
            'assigned_to',
            'plant',
            'zone',
            'location',
            'sublocation',
            'department',
            'scheduled_date',
            'due_date',
            'assignment_notes'
        ]
        widgets = {
            'template': forms.Select(attrs={
                'class': 'form-control'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select HOD'
            }),
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
            'department': forms.Select(attrs={
                'class': 'form-control'
            }),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'assignment_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any special instructions for the inspector'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter HODs only
        self.fields['assigned_to'].queryset = User.objects.filter(
            role__name='HOD',
            is_active_employee=True
        ).order_by('first_name', 'last_name')
        
        # Filter active templates
        self.fields['template'].queryset = InspectionTemplate.objects.filter(
            is_active=True
        )
        
        if user and not user.is_superuser:
            # Filter plants based on user access
            self.fields['plant'].queryset = Plant.objects.filter(
                id__in=[p.id for p in user.get_all_plants()]
            )
    
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


class QuestionFilterForm(forms.Form):
    """Filter form for question list"""
    
    category = forms.ModelChoiceField(
        queryset=InspectionCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    question_type = forms.ChoiceField(
        choices=[('', 'All Types')] + InspectionQuestion.QUESTION_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_critical = forms.NullBooleanField(
        required=False,
        widget=forms.Select(
            choices=[
                ('', 'All Questions'),
                ('true', 'Critical Only'),
                ('false', 'Non-Critical')
            ],
            attrs={'class': 'form-control'}
        )
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search questions...'
        })
    )
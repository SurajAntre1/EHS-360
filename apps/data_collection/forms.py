# apps/data_collection/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    MonthlyDataCollection,
    DataCollectionResponse,
    DataCollectionQuestion,
    DataCollectionCategory,
    DataCollectionAttachment,
    DataCollectionComment
)



class MonthlyDataCollectionForm(forms.ModelForm):
    """Main form for monthly data collection"""
    
    class Meta:
        model = MonthlyDataCollection
        fields = ['period', 'plant', 'zone', 'location', 'sublocation', 
                  'department', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'General remarks or notes about this data collection'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Auto-populate from user's assigned location if available
        if user and not self.instance.pk:
            if hasattr(user, 'plant') and user.plant:
                self.fields['plant'].initial = user.plant
                self.fields['plant'].widget = forms.HiddenInput()
            
            if hasattr(user, 'zone') and user.zone:
                self.fields['zone'].initial = user.zone
                self.fields['zone'].widget = forms.HiddenInput()
            
            if hasattr(user, 'location') and user.location:
                self.fields['location'].initial = user.location
                self.fields['location'].widget = forms.HiddenInput()
            
            if hasattr(user, 'sublocation') and user.sublocation:
                self.fields['sublocation'].initial = user.sublocation
                self.fields['sublocation'].widget = forms.HiddenInput()


class DynamicDataCollectionForm(forms.Form):
    """Dynamically generated form based on active questions"""
    
    def __init__(self, *args, **kwargs):
        plant = kwargs.pop('plant', None)
        collection = kwargs.pop('collection', None)
        super().__init__(*args, **kwargs)
        
        # Get all active questions
        questions = DataCollectionQuestion.objects.filter(
            is_active=True,
            category__is_active=True
        ).select_related('category').order_by(
            'category__display_order',
            'display_order'
        )
        
        # Filter by plant if applicable
        if plant:
            questions = questions.filter(
                models.Q(applicable_to_all_plants=True) |
                models.Q(applicable_plants=plant)
            )
        
        # Build form fields dynamically
        for question in questions:
            field_name = f'question_{question.id}'
            field_kwargs = {
                'label': question.question_text,
                'required': question.is_required,
                'help_text': question.help_text or ''
            }
            
            # Add appropriate field based on field_type
            if question.field_type == 'NUMBER':
                field = forms.DecimalField(
                    **field_kwargs,
                    max_digits=15,
                    decimal_places=2,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': question.placeholder or 'Enter numeric value',
                        'step': '0.01'
                    })
                )
                if question.min_value is not None:
                    field.validators.append(
                        forms.validators.MinValueValidator(question.min_value)
                    )
                if question.max_value is not None:
                    field.validators.append(
                        forms.validators.MaxValueValidator(question.max_value)
                    )
            
            elif question.field_type == 'TEXT':
                field = forms.CharField(
                    **field_kwargs,
                    max_length=question.max_length or 500,
                    min_length=question.min_length or None,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'placeholder': question.placeholder or 'Enter text'
                    })
                )
            
            elif question.field_type == 'TEXTAREA':
                field = forms.CharField(
                    **field_kwargs,
                    max_length=question.max_length or 2000,
                    min_length=question.min_length or None,
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 3,
                        'placeholder': question.placeholder or 'Enter detailed text'
                    })
                )
            
            elif question.field_type == 'DROPDOWN':
                choices = [('', '-- Select an option --')]
                options = question.get_options_list()
                choices.extend([(opt, opt) for opt in options])
                
                field = forms.ChoiceField(
                    **field_kwargs,
                    choices=choices,
                    widget=forms.Select(attrs={
                        'class': 'form-control'
                    })
                )
            
            elif question.field_type == 'RADIO':
                options = question.get_options_list()
                choices = [(opt, opt) for opt in options]
                
                field = forms.ChoiceField(
                    **field_kwargs,
                    choices=choices,
                    widget=forms.RadioSelect(attrs={
                        'class': 'form-check-input'
                    })
                )
            
            elif question.field_type == 'CHECKBOX':
                field = forms.BooleanField(
                    **field_kwargs,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input'
                    })
                )
            
            elif question.field_type == 'DATE':
                field = forms.DateField(
                    **field_kwargs,
                    widget=forms.DateInput(attrs={
                        'class': 'form-control',
                        'type': 'date'
                    })
                )
            
            elif question.field_type == 'EMAIL':
                field = forms.EmailField(
                    **field_kwargs,
                    widget=forms.EmailInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'email@example.com'
                    })
                )
            
            elif question.field_type == 'FILE':
                field = forms.FileField(
                    **field_kwargs,
                    widget=forms.FileInput(attrs={
                        'class': 'form-control-file'
                    })
                )
            
            else:
                # Default to text field
                field = forms.CharField(
                    **field_kwargs,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control'
                    })
                )
            
            self.fields[field_name] = field
            
            # Store question metadata for later use
            self.fields[field_name].question = question
            
            # Add unit field if question has unit_of_measurement
            if question.unit_of_measurement and question.field_type == 'NUMBER':
                unit_field_name = f'question_{question.id}_unit'
                self.fields[unit_field_name] = forms.CharField(
                    required=False,
                    initial=question.unit_of_measurement,
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'readonly': 'readonly',
                        'style': 'background-color: #e9ecef;'
                    })
                )
            
            # Add remarks field for each question
            remarks_field_name = f'question_{question.id}_remarks'
            self.fields[remarks_field_name] = forms.CharField(
                required=False,
                label='Remarks',
                widget=forms.Textarea(attrs={
                    'class': 'form-control',
                    'rows': 2,
                    'placeholder': 'Additional notes or comments (optional)'
                })
            )
        
        # Pre-populate with existing responses if collection exists
        if collection:
            existing_responses = DataCollectionResponse.objects.filter(
                collection=collection
            ).select_related('question')
            
            for response in existing_responses:
                field_name = f'question_{response.question.id}'
                
                if response.question.field_type == 'NUMBER':
                    self.fields[field_name].initial = response.numeric_value
                elif response.question.field_type in ['TEXT', 'TEXTAREA', 'EMAIL']:
                    self.fields[field_name].initial = response.text_value
                elif response.question.field_type == 'DATE':
                    self.fields[field_name].initial = response.date_value
                elif response.question.field_type == 'CHECKBOX':
                    self.fields[field_name].initial = response.boolean_value
                elif response.question.field_type in ['DROPDOWN', 'RADIO']:
                    self.fields[field_name].initial = response.selected_option
                
                # Set unit if present
                unit_field_name = f'question_{response.question.id}_unit'
                if unit_field_name in self.fields and response.unit_used:
                    self.fields[unit_field_name].initial = response.unit_used
                
                # Set remarks
                remarks_field_name = f'question_{response.question.id}_remarks'
                if remarks_field_name in self.fields:
                    self.fields[remarks_field_name].initial = response.remarks
    
    def get_questions_by_category(self):
        """Group questions by category for template rendering"""
        categories = {}
        
        for field_name, field in self.fields.items():
            if field_name.startswith('question_') and hasattr(field, 'question'):
                question = field.question
                category = question.category
                
                if category not in categories:
                    categories[category] = []
                
                # Get related fields (unit and remarks)
                question_id = question.id
                unit_field_name = f'question_{question_id}_unit'
                remarks_field_name = f'question_{question_id}_remarks'
                
                categories[category].append({
                    'question': question,
                    'field_name': field_name,
                    'field': field,
                    'unit_field': self.fields.get(unit_field_name),
                    'remarks_field': self.fields.get(remarks_field_name),
                })
        
        # Sort categories by display_order
        sorted_categories = sorted(
            categories.items(),
            key=lambda x: x[0].display_order
        )
        
        return sorted_categories


class DataCollectionAttachmentForm(forms.ModelForm):
    """Form for uploading additional attachments"""
    
    class Meta:
        model = DataCollectionAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of the file'
            })
        }


class DataCollectionCommentForm(forms.ModelForm):
    """Form for adding comments"""
    
    class Meta:
        model = DataCollectionComment
        fields = ['comment', 'is_internal']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your comment here...'
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class DataCollectionReviewForm(forms.Form):
    """Form for reviewing/approving data collection"""
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('request_changes', 'Request Changes'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Comments or feedback (optional for approval, required for rejection)'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        comments = cleaned_data.get('comments')
        
        if action == 'reject' and not comments:
            raise ValidationError('Comments are required when rejecting a collection')
        
        return cleaned_data
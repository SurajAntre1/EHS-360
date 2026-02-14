# apps/inspections/services.py

from django.utils import timezone
from apps.hazards.models import Hazard, HazardPhoto
from apps.inspections.models import InspectionSubmission, InspectionResponse, InspectionFinding
from django.db import transaction
import datetime


class InspectionHazardService:
    """
    Service to convert inspection findings (No answers) into hazard reports
    """
    
    @staticmethod
    @transaction.atomic
    def create_hazards_from_inspection(submission):
        """
        Auto-create hazard reports from inspection "No" answers
        
        Args:
            submission: InspectionSubmission instance
            
        Returns:
            List of created Hazard objects
        """
        created_hazards = []
        
        # Get all "No" responses where auto_generate_finding is True
        no_responses = InspectionResponse.objects.filter(
            submission=submission,
            answer='No',
            question__auto_generate_finding=True
        ).select_related('question', 'question__category')
        
        print(f"\n{'='*80}")
        print(f"🔄 Auto-creating hazards from inspection: {submission.schedule.schedule_code}")
        print(f"Found {no_responses.count()} 'No' answers to process")
        print(f"{'='*80}\n")
        
        for response in no_responses:
            try:
                hazard = InspectionHazardService._create_hazard_from_response(
                    submission, 
                    response
                )
                created_hazards.append(hazard)
                
                # Link finding to hazard if finding exists
                finding = InspectionFinding.objects.filter(
                    submission=submission,
                    question=response.question
                ).first()
                
                if finding:
                    # Store hazard reference in finding (you may need to add this field)
                    # finding.related_hazard = hazard
                    # finding.save()
                    pass
                    
            except Exception as e:
                print(f"❌ Error creating hazard for question {response.question.question_code}: {e}")
                continue
        
        print(f"\n✅ Created {len(created_hazards)} hazards from inspection\n")
        return created_hazards
    
    @staticmethod
    def _create_hazard_from_response(submission, response):
        """
        Create a single hazard from an inspection response
        """
        question = response.question
        schedule = submission.schedule
        
        # Determine severity based on question criticality
        if question.is_critical:
            severity = 'high'
        else:
            severity = 'medium'
        
        # Determine hazard type - default to UC (Unsafe Condition)
        hazard_type = 'UC'
        
        # Map category to hazard category
        hazard_category = InspectionHazardService._map_inspection_to_hazard_category(
            question.category.category_code
        )
        
        # Create hazard title
        hazard_title = f"Inspection Finding - {question.category.category_name}"
        
        # Create hazard description
        hazard_description = f"""
**Inspection Finding**

**Question:** {question.question_text}

**Answer:** No

**Inspector's Remarks:** {response.remarks or 'No remarks provided'}

**Inspection Details:**
- Inspection Code: {schedule.schedule_code}
- Template: {schedule.template.template_name}
- Conducted by: {submission.submitted_by.get_full_name()}
- Date: {submission.submitted_at.strftime('%Y-%m-%d %H:%M')}

**Reference Standard:** {question.reference_standard or 'N/A'}
**Guidance Notes:** {question.guidance_notes or 'N/A'}
        """.strip()
        
        # Create the hazard
        hazard = Hazard.objects.create(
            # Basic Info
            hazard_type=hazard_type,
            hazard_category=hazard_category,
            hazard_title=hazard_title,
            hazard_description=hazard_description,
            severity=severity,
            
            # Location from inspection
            plant=schedule.plant,
            zone=schedule.zone,
            location=schedule.location,
            sublocation=schedule.sublocation,
            
            # Reporter info (from inspector)
            reported_by=submission.submitted_by,
            reporter_name=submission.submitted_by.get_full_name(),
            reporter_email=submission.submitted_by.email,
            reporter_phone=getattr(submission.submitted_by, 'phone', ''),
            
            # Timing
            incident_datetime=submission.submitted_at,
            
            # Status
            status='REPORTED',
            approval_status='PENDING',
            
            # Metadata
            report_source='inspection_auto_generated',
        )
        
        # Generate report number
        today = timezone.now().date()
        plant_code = hazard.plant.code if hazard.plant else 'UNKN'
        count = Hazard.objects.filter(created_at__date=today).count()
        hazard.report_number = f"HAZ-{plant_code}-{today:%Y%m%d}-{count:03d}"
        
        # Set deadline based on severity
        severity_days = {'low': 30, 'medium': 15, 'high': 7, 'critical': 1}
        hazard.action_deadline = today + timezone.timedelta(
            days=severity_days.get(severity, 15)
        )
        
        hazard.save()
        
        print(f"  ✅ Created hazard: {hazard.report_number} for question {question.question_code}")
        
        # Copy photo if exists
        if response.photo:
            try:
                HazardPhoto.objects.create(
                    hazard=hazard,
                    photo=response.photo,
                    photo_type='evidence',
                    description=f"Photo from inspection response - {question.question_code}",
                    uploaded_by=submission.submitted_by
                )
                print(f"    📸 Copied photo from inspection response")
            except Exception as e:
                print(f"    ⚠️ Could not copy photo: {e}")
        
        return hazard
    
    @staticmethod
    def _map_inspection_to_hazard_category(category_code):
        """
        Map inspection category codes to hazard categories
        """
        mapping = {
            'FS': 'fire',              # Fire Safety → Fire
            'ES': 'electrical',        # Electrical Safety → Electrical
            'HK': 'slip_trip_fall',    # Housekeeping → Slip/Trip/Fall
            'CS': 'chemical',          # Chemical Safety → Chemical
            'MS': 'equipment',         # Machine Safety → Equipment
            'WH': 'working_at_height', # Work at Height → Working at Height
            'PPE': 'other',            # PPE → Other
            'ER': 'ergonomic',         # Ergonomics → Ergonomic
        }
        
        return mapping.get(category_code, 'other')
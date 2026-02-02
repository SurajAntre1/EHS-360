
from django.db.models import Count, Q, Sum
from datetime import datetime, date
import calendar
import json


class EnvironmentalDataFetcher:
    """
    Dynamic data fetcher for auto-calculated environmental questions
    """
    
    @classmethod
    def get_data_for_plant_year(cls, plant, year):
        """
        Returns auto-calculated values for all questions dynamically
        Format: {'Question Text': {'January': 5, 'February': 3, ...}}
        """
        from .models import EnvironmentalQuestion
        
        result = {}
        
        # ✅ UPDATED: Include INSPECTION source type
        auto_questions = EnvironmentalQuestion.objects.filter(
            is_active=True,
            source_type__in=['INCIDENT', 'HAZARD', 'INSPECTION']  # ⬅️ ADDED INSPECTION
        )
        
        MONTHS = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        for question in auto_questions:
            month_data = {}
            
            for month_num, month_name in enumerate(MONTHS, start=1):
                count = cls.calculate_question_value(
                    question, plant, month_num, year
                )
                month_data[month_name] = count
            
            result[question.question_text] = month_data
        
        return result
    
    @classmethod
    def calculate_question_value(cls, question, plant, month, year):
        """Calculate value for a specific question, plant, and month"""
        
        if question.source_type == 'INCIDENT':
            from apps.accidents.models import Incident

            queryset = Incident.objects.filter(
                plant=plant,
                incident_date__month=month,
                incident_date__year=year
            )
            
            # ✅ Apply primary filter - incident_type is ForeignKey (use _id)
            if question.filter_field == 'incident_type' and question.filter_value:
                queryset = queryset.filter(incident_type_id=question.filter_value)
            elif question.filter_field == 'status' and question.filter_value:
                queryset = queryset.filter(status=question.filter_value)
            elif question.filter_field == 'plant' and question.filter_value:
                queryset = queryset.filter(plant_id=question.filter_value)
            
            # ✅ Apply secondary filter
            if question.filter_field_2 and question.filter_value_2:
                if question.filter_field_2 == 'incident_type':
                    queryset = queryset.filter(incident_type_id=question.filter_value_2)
                elif question.filter_field_2 == 'status':
                    queryset = queryset.filter(status=question.filter_value_2)
                elif question.filter_field_2 == 'plant':
                    queryset = queryset.filter(plant_id=question.filter_value_2)
            
            return queryset.count()
        
        elif question.source_type == 'HAZARD':
            try:
                from apps.hazards.models import Hazard
                
                # ✅ Use incident_datetime (DateTimeField)
                queryset = Hazard.objects.filter(
                    plant=plant,
                    incident_datetime__year=year,
                    incident_datetime__month=month
                )
                
                # ✅ Apply primary filter - hazard_type is CharField (NO _id)
                if question.filter_field == 'hazard_type' and question.filter_value:
                    queryset = queryset.filter(hazard_type=question.filter_value)
                elif question.filter_field == 'severity' and question.filter_value:
                    queryset = queryset.filter(severity=question.filter_value)
                elif question.filter_field == 'status' and question.filter_value:
                    queryset = queryset.filter(status=question.filter_value)
                elif question.filter_field == 'plant' and question.filter_value:
                    queryset = queryset.filter(plant_id=question.filter_value)
                
                # ✅ Apply secondary filter
                if question.filter_field_2 and question.filter_value_2:
                    if question.filter_field_2 == 'hazard_type':
                        queryset = queryset.filter(hazard_type=question.filter_value_2)
                    elif question.filter_field_2 == 'severity':
                        queryset = queryset.filter(severity=question.filter_value_2)
                    elif question.filter_field_2 == 'status':
                        queryset = queryset.filter(status=question.filter_value_2)
                    elif question.filter_field_2 == 'plant':
                        queryset = queryset.filter(plant_id=question.filter_value_2)
                
                return queryset.count()
            
            except ImportError:
                return 0
            except Exception as e:
                print(f"Error calculating hazard data: {e}")
                import traceback
                traceback.print_exc()
                return 0
        
        # ========================================
        # ⬇️ NEW SECTION: INSPECTION CALCULATION
        # ========================================
        elif question.source_type == 'INSPECTION':
            try:
                from apps.inspections.models import InspectionSchedule, InspectionTemplate
                
                # Base queryset - filter by plant, month, year
                queryset = InspectionSchedule.objects.filter(
                    plant=plant,
                    scheduled_date__month=month,
                    scheduled_date__year=year
                )
                
                # ✅ Apply primary filter
                if question.filter_field and question.filter_value:
                    if question.filter_field == 'template':
                        # Template is ForeignKey, use _id
                        queryset = queryset.filter(template_id=question.filter_value)
                    
                    elif question.filter_field == 'inspection_type':
                        # Filter by template's inspection_type
                        queryset = queryset.filter(template__inspection_type=question.filter_value)
                    
                    elif question.filter_field == 'status':
                        # Status is CharField on InspectionSchedule
                        queryset = queryset.filter(status=question.filter_value)
                    
                    elif question.filter_field == 'plant':
                        # Plant is ForeignKey, use _id
                        queryset = queryset.filter(plant_id=question.filter_value)
                    
                    elif question.filter_field == 'assigned_to':
                        # Assigned to is ForeignKey (User), use _id
                        queryset = queryset.filter(assigned_to_id=question.filter_value)
                
                # ✅ Apply secondary filter (optional)
                if question.filter_field_2 and question.filter_value_2:
                    if question.filter_field_2 == 'template':
                        queryset = queryset.filter(template_id=question.filter_value_2)
                    
                    elif question.filter_field_2 == 'inspection_type':
                        queryset = queryset.filter(template__inspection_type=question.filter_value_2)
                    
                    elif question.filter_field_2 == 'status':
                        queryset = queryset.filter(status=question.filter_value_2)
                    
                    elif question.filter_field_2 == 'plant':
                        queryset = queryset.filter(plant_id=question.filter_value_2)
                    
                    elif question.filter_field_2 == 'assigned_to':
                        queryset = queryset.filter(assigned_to_id=question.filter_value_2)
                
                return queryset.count()
            
            except ImportError:
                # Inspection module not installed
                print("Inspection module not found")
                return 0
            except Exception as e:
                print(f"Error calculating inspection data: {e}")
                import traceback
                traceback.print_exc()
                return 0
        
        # Default return for unknown source types
        return 0
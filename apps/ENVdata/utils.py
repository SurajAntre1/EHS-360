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
        
        # Get all auto-calculated questions
        auto_questions = EnvironmentalQuestion.objects.filter(
            is_active=True,
            source_type__in=['INCIDENT', 'HAZARD']
        )
        
        for question in auto_questions:
            question_data = cls._calculate_question_data(
                plant=plant,
                year=year,
                question=question
            )
            
            if question_data:
                result[question.question_text] = question_data
        
        return result
    
    @classmethod
    def _calculate_question_data(cls, plant, year, question):
        """
        Calculate monthly data dynamically based on question configuration
        """
        from apps.accidents.models import Incident
        from apps.hazards.models import Hazard
        
        monthly_data = {}
        
        # Get the model and date field
        if question.source_type == 'INCIDENT':
            model = Incident
            date_field = 'incident_date'
        elif question.source_type == 'HAZARD':
            model = Hazard
            date_field = 'incident_datetime'
        else:
            return monthly_data
        
        # Build dynamic filter criteria
        filter_criteria = {'plant': plant}
        
        # Add PRIMARY filter
        if question.filter_field and question.filter_value:
            filter_criteria[question.filter_field] = question.filter_value
        
        # Add SECONDARY filter
        if question.filter_field_2 and question.filter_value_2:
            filter_criteria[question.filter_field_2] = question.filter_value_2
        
        # Loop through each month
        for month_num in range(1, 13):
            month_name = calendar.month_name[month_num]
            
            # Get date range for this month
            start_date = date(year, month_num, 1)
            last_day = calendar.monthrange(year, month_num)[1]
            end_date = date(year, month_num, last_day)
            
            # Build query with date filter
            if question.source_type == 'INCIDENT':
                query_filters = {
                    **filter_criteria,
                    f'{date_field}__gte': start_date,
                    f'{date_field}__lte': end_date,
                }
            else:  # HAZARD
                query_filters = {
                    **filter_criteria,
                    f'{date_field}__date__gte': start_date,
                    f'{date_field}__date__lte': end_date,
                }
            
            # Execute query
            try:
                count = model.objects.filter(**query_filters).count()
                monthly_data[month_name] = count
            except Exception as e:
                print(f"Error calculating data for {question.question_text}: {e}")
                monthly_data[month_name] = 0
        
        return monthly_data
    
    @classmethod
    def get_available_fields(cls, source_type):
        """
        Get available fields for a given source type
        """
        from apps.accidents.models import Incident
        from apps.hazards.models import Hazard
        
        if source_type == 'INCIDENT':
            model = Incident
        elif source_type == 'HAZARD':
            model = Hazard
        else:
            return []
        
        fields = []
        for field in model._meta.get_fields():
            if not field.auto_created and not field.many_to_many and not field.one_to_many:
                fields.append({
                    'name': field.name,
                    'type': field.get_internal_type()
                })
        
        return fields
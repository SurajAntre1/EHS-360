from openpyxl import Workbook
from .models import MonthlyIndicatorData, EnvironmentalQuestion
from apps.organizations.models import Plant
from .constants import MONTHS
from openpyxl.styles import Font, Alignment
from django.db.models import Q, Count
from apps.accidents.models import Incident
from apps.hazards.models import Hazard
from datetime import datetime, date
import calendar

def generate_environmental_excel(plants_data, months):
    wb = Workbook()
    ws = wb.active
    ws.title = "Environmental Data"
    headers = ["Plant", "Questions", "Unit", "Annual"] + months
    ws.append(headers)

    bold_font = Font(bold=True)
    for cell in ws[1]:
        cell.font = bold_font
        cell.alignment = Alignment(horizontal='center')
    ws.freeze_panes = 'A2'
    for plant_data in plants_data:
        plant_name = plant_data["plant"].name
        for q in plant_data["questions_data"]:
            row = [plant_name,q["question"],q["unit"],q["annual"],]
            for month in months:
                row.append(q["month_data"].get(month, ""))
            ws.append(row)
    
    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:
            try:
                max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[column_letter].width = max_length + 2
    return wb

def get_all_plants_environmental_data(plants):
    questions = EnvironmentalQuestion.objects.filter(is_active=True).select_related("default_unit").order_by("order")
    all_data = MonthlyIndicatorData.objects.filter(plant__in=plants).select_related("plant")
    plants_data = []
    for plant in plants:
        questions_data = []
        for q in questions:
            month_data = {}
            total = 0
            has_values = False
            unit_name = q.default_unit.name if q.default_unit else "Count"
            for month in MONTHS:
                month_key = month.lower()[:3]
                entry = all_data.filter(
                    plant=plant,
                    indicator=q.question_text,
                    month=month_key
                ).first()

                value = entry.value if entry else ""
                if value:
                    try:
                        total += float(str(value).replace(",", ""))
                        has_values = True
                    except (ValueError, TypeError):
                        pass
                month_data[month] = value

            questions_data.append({
                "question": q.question_text,
                "unit": unit_name,
                "month_data": month_data,
                "annual": f"{total:,.2f}" if has_values else "",
            })

        plants_data.append({"plant": plant,"questions_data": questions_data,})

    return plants_data




###automatically datafetch in the data collection from accident and hazard 

# apps/ENVdata/utils.py

from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth
from apps.accidents.models import Incident
from apps.hazards.models import Hazard
import datetime

class EnvironmentalDataFetcher:
    """
    Fetches environmental data from Incident and Hazard modules
    for auto-populating predefined environmental questions
    """
    
    # Mapping of question text to data fetching methods
    QUESTION_MAPPING = {
        "Fatalities": "get_fatalities_data",
        "Lost Time Injuries (LTI)": "get_lti_data",
        "MTC (Medical Treatment Case)": "get_mtc_data",
        "First aid cases": "get_first_aid_data",
        "Fire Incidents": "get_fire_incidents_data",
        "Near Miss Reported": "get_near_miss_reported_data",
        "Near Miss Closed": "get_near_miss_closed_data",
        "Observations (UA/UC) reported": "get_observations_reported_data",
        "Observations (UA/UC) Closed": "get_observations_closed_data",
        "Observations related to LSR/SIP reported": "get_lsr_sip_reported_data",
        "Observations related to LSR/SIP closed": "get_lsr_sip_closed_data",
        "Safety Inspections with Leadership Team": "get_safety_inspections_data",
        "Points Identified in leadership team reported": "get_points_identified_reported_data",
        "Points Identified in leadership team closed": "get_points_identified_closed_data",
        "Asbestos walkthrough carried out by plant leadership": "get_asbestos_walkthrough_data",
        "Asbestos walkthrough points reported": "get_asbestos_points_reported_data",
        "Asbestos walkthrough points closed": "get_asbestos_points_closed_data",
        "Total inspections carried out": "get_total_inspections_data",
    }
    
    MONTH_NAMES = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    
    @classmethod
    def get_data_for_plant_year(cls, plant, year):
        """
        Main method to fetch all auto-populated data for a plant and year
        
        Args:
            plant: Plant object
            year: Integer year (e.g., 2025)
            
        Returns:
            Dictionary with question_text as key and month-wise data as value
            Example: {
                "Fatalities": {
                    "January": 2,
                    "February": 1,
                    ...
                },
                ...
            }
        """
        result = {}
        
        for question_text, method_name in cls.QUESTION_MAPPING.items():
            method = getattr(cls, method_name)
            result[question_text] = method(plant, year)
        
        return result
    
    # ==================== INCIDENT RELATED METHODS ====================
    
    @staticmethod
    def get_fatalities_data(plant, year):
        """Get Fatalities count by month"""
        return EnvironmentalDataFetcher._get_incident_count_by_month(
            plant, year, incident_type='FATALITY'
        )
    
    @staticmethod
    def get_lti_data(plant, year):
        """Get Lost Time Injuries count by month"""
        return EnvironmentalDataFetcher._get_incident_count_by_month(
            plant, year, incident_type='LTI'
        )
    
    @staticmethod
    def get_mtc_data(plant, year):
        """Get Medical Treatment Cases count by month"""
        return EnvironmentalDataFetcher._get_incident_count_by_month(
            plant, year, incident_type='MTC'
        )
    
    @staticmethod
    def get_first_aid_data(plant, year):
        """Get First Aid cases count by month"""
        return EnvironmentalDataFetcher._get_incident_count_by_month(
            plant, year, incident_type='FA'
        )
    
    @staticmethod
    def get_fire_incidents_data(plant, year):
        """Get Fire Incidents count by month (from incidents with fire-related unsafe conditions)"""
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            count = Incident.objects.filter(
                plant=plant,
                incident_date__year=year,
                incident_date__month=month_num,
                unsafe_conditions__icontains='fire'  # Adjust based on your actual data structure
            ).count()
            
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
    
    # ==================== HAZARD RELATED METHODS ====================
    
    @staticmethod
    def get_near_miss_reported_data(plant, year):
        """Get Near Miss reported count by month"""
        return EnvironmentalDataFetcher._get_hazard_count_by_month(
            plant, year, hazard_type='NM'
        )
    
    @staticmethod
    def get_near_miss_closed_data(plant, year):
        """Get Near Miss closed count by month"""
        return EnvironmentalDataFetcher._get_hazard_count_by_month(
            plant, year, hazard_type='NM', status='CLOSED'
        )
    
    @staticmethod
    def get_observations_reported_data(plant, year):
        """Get Observations (UA/UC) reported count by month"""
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            count = Hazard.objects.filter(
                plant=plant,
                incident_datetime__year=year,
                incident_datetime__month=month_num,
                hazard_type__in=['UA', 'UC']
            ).count()
            
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
    
    @staticmethod
    def get_observations_closed_data(plant, year):
        """Get Observations (UA/UC) closed count by month"""
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            count = Hazard.objects.filter(
                plant=plant,
                incident_datetime__year=year,
                incident_datetime__month=month_num,
                hazard_type__in=['UA', 'UC'],
                status='CLOSED'
            ).count()
            
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
    
    @staticmethod
    def get_lsr_sip_reported_data(plant, year):
        """Get LSR/SIP observations reported count by month"""
        # This would depend on how you track LSR/SIP in your system
        # Adjust the filter condition based on your actual implementation
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            # Example: Assuming you have a category or tag for LSR/SIP
            count = Hazard.objects.filter(
                plant=plant,
                incident_datetime__year=year,
                incident_datetime__month=month_num,
                # Add your LSR/SIP identification logic here
                # For example: hazard_category__in=['lsr', 'sip']
            ).count()
            
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
    
    @staticmethod
    def get_lsr_sip_closed_data(plant, year):
        """Get LSR/SIP observations closed count by month"""
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            count = Hazard.objects.filter(
                plant=plant,
                incident_datetime__year=year,
                incident_datetime__month=month_num,
                status='CLOSED'
                # Add your LSR/SIP identification logic here
            ).count()
            
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
    
    # ==================== INSPECTION RELATED METHODS ====================
    # Note: These require an Inspection model which I don't see in your provided code
    # You'll need to adjust these based on your actual inspection tracking system
    
    @staticmethod
    def get_safety_inspections_data(plant, year):
        """Get Safety Inspections with Leadership Team count by month"""
        # Placeholder - adjust based on your inspection model
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your inspection fetching logic here
            # Example: from apps.inspections.models import Inspection
            # count = Inspection.objects.filter(...)
            months_data[month_name] = ''
        
        return months_data
    
    @staticmethod
    def get_points_identified_reported_data(plant, year):
        """Get Points identified in leadership team reported by month"""
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your logic here
            months_data[month_name] = ''
        
        return months_data
    
    @staticmethod
    def get_points_identified_closed_data(plant, year):
        """Get Points identified in leadership team closed by month"""
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your logic here
            months_data[month_name] = ''
        
        return months_data
    
    @staticmethod
    def get_asbestos_walkthrough_data(plant, year):
        """Get Asbestos walkthrough carried out by plant leadership by month"""
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your logic here
            months_data[month_name] = ''
        
        return months_data
    
    @staticmethod
    def get_asbestos_points_reported_data(plant, year):
        """Get Asbestos walkthrough points reported by month"""
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your logic here
            months_data[month_name] = ''
        
        return months_data
    
    @staticmethod
    def get_asbestos_points_closed_data(plant, year):
        """Get Asbestos walkthrough points closed by month"""
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your logic here
            months_data[month_name] = ''
        
        return months_data
    
    @staticmethod
    def get_total_inspections_data(plant, year):
        """Get Total inspections carried out by month"""
        months_data = {}
        
        for month_name in EnvironmentalDataFetcher.MONTH_NAMES:
            # Add your logic here
            months_data[month_name] = ''
        
        return months_data
    
    # ==================== HELPER METHODS ====================
    
    @staticmethod
    def _get_incident_count_by_month(plant, year, incident_type=None):
        """
        Helper method to get incident count by month
        
        Args:
            plant: Plant object
            year: Integer year
            incident_type: String incident type (e.g., 'LTI', 'MTC', 'FA', 'FATALITY')
        
        Returns:
            Dictionary with month names as keys and counts as values
        """
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            query = Q(
                plant=plant,
                incident_date__year=year,
                incident_date__month=month_num
            )
            
            if incident_type:
                query &= Q(incident_type=incident_type)
            
            count = Incident.objects.filter(query).count()
            
            # Only add non-zero values (or empty string for zero)
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
    
    @staticmethod
    def _get_hazard_count_by_month(plant, year, hazard_type=None, status=None):
        """
        Helper method to get hazard count by month
        
        Args:
            plant: Plant object
            year: Integer year
            hazard_type: String hazard type (e.g., 'UA', 'UC', 'NM')
            status: String status (e.g., 'CLOSED', 'RESOLVED')
        
        Returns:
            Dictionary with month names as keys and counts as values
        """
        months_data = {}
        
        for month_num, month_name in enumerate(EnvironmentalDataFetcher.MONTH_NAMES, start=1):
            query = Q(
                plant=plant,
                incident_datetime__year=year,
                incident_datetime__month=month_num
            )
            
            if hazard_type:
                query &= Q(hazard_type=hazard_type)
            
            if status:
                query &= Q(status=status)
            
            count = Hazard.objects.filter(query).count()
            
            # Only add non-zero values (or empty string for zero)
            months_data[month_name] = count if count > 0 else ''
        
        return months_data
from openpyxl import Workbook
from .models import MonthlyIndicatorData, EnvironmentalQuestion
from apps.organizations.models import Plant
from .constants import MONTHS
from openpyxl.styles import Font, Alignment
from django.db.models import Q, Count
from apps.accidents.models import Incident
from apps.hazards.models import Hazard
from datetime import datetime

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
class EnvironmentalDataFetcher:
    """
    Helper class to fetch environmental data from Incident and Hazard modules
    """
    
    @staticmethod
    def get_month_range(year, month):
        """Get start and end date for a given month"""
        month_num = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }.get(month.lower())
        
        if not month_num:
            return None, None
            
        start_date = datetime(year, month_num, 1)
        
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month_num + 1, 1)
            
        return start_date, end_date
    
    @staticmethod
    def fetch_data_for_question(question_text, plant, year, month):
        """
        Fetch count for a specific question from Incident/Hazard modules
        Returns: integer count or None
        """
        start_date, end_date = EnvironmentalDataFetcher.get_month_range(year, month)
        
        if not start_date or not end_date:
            return None
        
        question_lower = question_text.lower().strip()
        
        # FATALITIES
        if 'fatalities' in question_lower or 'fatality' in question_lower:
            return Incident.objects.filter(
                plant=plant,
                incident_date__gte=start_date.date(),
                incident_date__lt=end_date.date(),
                incident_type='FATALITY'
            ).count()
        
        # LOST TIME INJURIES (LTI)
        elif 'lost time injuries' in question_lower or 'lti' in question_lower:
            return Incident.objects.filter(
                plant=plant,
                incident_date__gte=start_date.date(),
                incident_date__lt=end_date.date(),
                incident_type='LTI'
            ).count()
        
        # MEDICAL TREATMENT CASE (MTC)
        elif 'mtc' in question_lower or 'medical treatment case' in question_lower:
            return Incident.objects.filter(
                plant=plant,
                incident_date__gte=start_date.date(),
                incident_date__lt=end_date.date(),
                incident_type='MTC'
            ).count()
        
        # FIRST AID CASES
        elif 'first aid' in question_lower:
            return Incident.objects.filter(
                plant=plant,
                incident_date__gte=start_date.date(),
                incident_date__lt=end_date.date(),
                incident_type='FA'
            ).count()
        
        # FIRE INCIDENTS
        elif 'fire incidents' in question_lower or 'fire incident' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date,
                hazard_category='fire'
            ).count()
        
        # NEAR MISS REPORTED
        elif 'near miss reported' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date,
                hazard_type='NM'
            ).count()
        
        # NEAR MISS CLOSED
        elif 'near miss closed' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date,
                hazard_type='NM',
                status='CLOSED'
            ).count()
        
        # OBSERVATIONS (UA/UC) REPORTED
        elif 'observations' in question_lower and 'ua/uc' in question_lower and 'reported' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date,
                hazard_type__in=['UA', 'UC']
            ).count()
        
        # OBSERVATIONS (UA/UC) CLOSED
        elif 'observations' in question_lower and 'ua/uc' in question_lower and 'closed' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date,
                hazard_type__in=['UA', 'UC'],
                status='CLOSED'
            ).count()
        
        # OBSERVATIONS RELATED TO LSR/SIP REPORTED
        elif 'lsr/sip' in question_lower and 'reported' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date
            ).filter(
                Q(hazard_description__icontains='LSR') | Q(hazard_description__icontains='SIP')
            ).count()
        
        # OBSERVATIONS RELATED TO LSR/SIP CLOSED
        elif 'lsr/sip' in question_lower and 'closed' in question_lower:
            return Hazard.objects.filter(
                plant=plant,
                incident_datetime__gte=start_date,
                incident_datetime__lt=end_date,
                status='CLOSED'
            ).filter(
                Q(hazard_description__icontains='LSR') | Q(hazard_description__icontains='SIP')
            ).count()
        
        # SAFETY INSPECTIONS WITH LEADERSHIP TEAM
        # Add custom logic if you have inspection module
        
        # Default: return None for manual entry
        return None
    
    @staticmethod
    def get_auto_populated_data(plant, year):
        """
        Get all auto-populated data for a plant for the entire year
        Returns: dict with question_text as key and month_data dict as value
        """
        from apps.ENVdata.models import EnvironmentalQuestion
        
        questions = EnvironmentalQuestion.objects.filter(
            is_active=True
        ).order_by("order", "id")
        
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        auto_data = {}
        
        for question in questions:
            month_data = {}
            for month in months:
                count = EnvironmentalDataFetcher.fetch_data_for_question(
                    question.question_text,
                    plant,
                    year,
                    month
                )
                if count is not None:
                    month_data[month] = str(count)
            
            if month_data:
                auto_data[question.question_text] = month_data
        
        return auto_data


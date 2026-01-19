from openpyxl import Workbook
from .models import MonthlyIndicatorData, EnvironmentalQuestion
from apps.organizations.models import Plant
from .constants import MONTHS
from openpyxl.styles import Font, Alignment


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


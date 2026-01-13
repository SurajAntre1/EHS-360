from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.organizations.models import Plant
from .models import MonthlyIndicatorData
from .constants import ENVIRONMENTAL_QUESTIONS, MONTHS

class PlantMonthlyEntryView(LoginRequiredMixin, View):
    template_name = "data_collection/data_env.html"
    
    CONVERSION_FACTORS = {
        'MT': {'MT': 1, 'kg': 1000, 'lbs': 2204.62, 'cubic-m': 0.45},
        'kg': {'MT': 0.001, 'kg': 1, 'lbs': 2.20462, 'cubic-m': 0.00045},
        'lbs': {'MT': 0.000453592, 'kg': 0.453592, 'lbs': 1, 'cubic-m': 0.000204},
        'cubic-m': {'MT': 2.22, 'kg': 2222.22, 'lbs': 4900, 'cubic-m': 1},
        'KL': {'KL': 1, 'm³': 1, 'Liters': 1000},
        'm³': {'KL': 1, 'm³': 1, 'Liters': 1000},
        'Liters': {'KL': 0.001, 'm³': 0.001, 'Liters': 1},
        'kWh': {'kWh': 1, 'MWh': 0.001, 'GJ': 0.0036},
        'MWh': {'kWh': 1000, 'MWh': 1, 'GJ': 3.6},
        'GJ': {'kWh': 277.778, 'MWh': 0.277778, 'GJ': 1},
        'Days': {'Days': 1, 'Hours': 24},
        'Hours': {'Days': 0.0416667, 'Hours': 1},
        'mg/m³': {'mg/m³': 1, 'µg/m³': 1000},
        'µg/m³': {'mg/m³': 0.001, 'µg/m³': 1},
        '%': {'%': 1, 'PPM': 10000},
        'PPM': {'%': 0.0001, 'PPM': 1},
        'mg/L': {'mg/L': 1, 'ppm': 1},
        'ppm': {'mg/L': 1, 'ppm': 1},
        'Count': {'Count': 1, 'Rate': 1, 'Percentage': 1},
        'Rate': {'Count': 1, 'Rate': 1, 'Percentage': 1},
        'Percentage': {'Count': 1, 'Rate': 1, 'Percentage': 1},
        'Yes/No': {'Yes/No': 1}
    }

    def get_plant(self, request):
        return Plant.objects.filter(users=request.user, is_active=True).first()
    
    def convert_value(self, value, from_unit, to_unit):
        if from_unit == to_unit:
            return value
        
        if from_unit in ['Count', 'Rate', 'Percentage', 'Yes/No'] or to_unit in ['Yes/No']:
            return value
        
        if from_unit in self.CONVERSION_FACTORS and to_unit in self.CONVERSION_FACTORS[from_unit]:
            factor = self.CONVERSION_FACTORS[from_unit][to_unit]
            return value * factor
        
        return value
    
    def get_base_unit(self, question_text):
        for item in ENVIRONMENTAL_QUESTIONS:
            if item['question'] == question_text:
                return item['default_unit']
        return None

    def get(self, request):
        plant = self.get_plant(request)
        if not plant:
            return render(request, "no_plant_assigned.html")

        saved_data = MonthlyIndicatorData.objects.filter(plant=plant)
        
        data_dict = {}
        unit_dict = {}
        
        for d in saved_data:
            if d.indicator not in data_dict:
                data_dict[d.indicator] = {}
                # Get saved unit or default
                unit_dict[d.indicator] = d.unit if d.unit else self.get_base_unit(d.indicator)
            
            # Get base unit and saved unit
            base_unit = self.get_base_unit(d.indicator)
            saved_unit = unit_dict[d.indicator]
            
            try:
                # Value in DB is stored in BASE unit
                stored_value = float(d.value) if d.value else 0
                
                # Convert from BASE unit to SAVED unit for display
                display_value = self.convert_value(stored_value, base_unit, saved_unit)
                
                data_dict[d.indicator][d.month.capitalize()] = display_value
            except (ValueError, TypeError):
                data_dict[d.indicator][d.month.capitalize()] = d.value

        context = {
            "plant": plant,
            "questions": ENVIRONMENTAL_QUESTIONS,
            "months": MONTHS,
            "data": data_dict,
            "unit_dict": unit_dict,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        plant = self.get_plant(request)
        if not plant:
            return redirect("plant-entry")

        for item in ENVIRONMENTAL_QUESTIONS:
            question_text = item['question']
            base_unit = item['default_unit']
            
            unit_field_name = f"unit_{question_text}".lower() \
                .replace(" ", "-") \
                .replace("/", "-") \
                .replace("(", "") \
                .replace(")", "") \
                .replace("+", "") \
                .replace(",", "") \
                .replace(".", "") \
                .replace(";", "") \
                .replace("'", "")
            
            selected_unit = request.POST.get(unit_field_name, base_unit)
            
            for month in MONTHS:
                field_name = f"{question_text}_{month}".lower() \
                    .replace(" ", "-") \
                    .replace("/", "-") \
                    .replace("(", "") \
                    .replace(")", "") \
                    .replace("+", "") \
                    .replace(",", "") \
                    .replace(".", "") \
                    .replace(";", "") \
                    .replace("'", "")

                value = request.POST.get(field_name, "").strip()

                if value:
                    try:
                        numeric_value = float(value)
                        # Convert from SELECTED unit to BASE unit for storage
                        stored_value = self.convert_value(numeric_value, selected_unit, base_unit)
                        
                        MonthlyIndicatorData.objects.update_or_create(
                            plant=plant,
                            indicator=question_text,
                            month=month.lower()[:3],
                            defaults={
                                "value": str(stored_value),
                                "unit": selected_unit,
                                "created_by": request.user
                            }
                        )
                    except (ValueError, TypeError):
                        continue

        return redirect("plant-entry")
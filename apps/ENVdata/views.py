from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.organizations.models import Plant
from .models import MonthlyIndicatorData
from .constants import ENVIRONMENTAL_QUESTIONS, MONTHS

class PlantMonthlyEntryView(LoginRequiredMixin, View):
    template_name = "data_collection/data_env.html"

    def get_plant(self, request):
        """
        Returns the first plant assigned to the logged-in user
        """
        return Plant.objects.filter(users=request.user, is_active=True).first()

    def get(self, request):
        plant = self.get_plant(request)
        if not plant:
            return render(request, "no_plant_assigned.html")

        # Fetch saved data
        saved_data = MonthlyIndicatorData.objects.filter(plant=plant)
        
        # Build nested dictionary structure for template
        # Format: {question_text: {month: value}}
        data_dict = {}
        for d in saved_data:
            if d.indicator not in data_dict:
                data_dict[d.indicator] = {}
            data_dict[d.indicator][d.month.capitalize()] = d.value

        context = {
            "plant": plant,
            "questions": ENVIRONMENTAL_QUESTIONS,  # Now passing list of dicts
            "months": MONTHS,
            "data": data_dict,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        plant = self.get_plant(request)
        if not plant:
            return redirect("plant-entry")

        # Iterate through structured questions
        for item in ENVIRONMENTAL_QUESTIONS:
            question_text = item['question']
            
            for month in MONTHS:
                # Generate field name using slugify logic
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
                    MonthlyIndicatorData.objects.update_or_create(
                        plant=plant,
                        indicator=question_text,
                        month=month.lower()[:3],  # Store as 'jan', 'feb', etc.
                        defaults={
                            "value": value,
                            "created_by": request.user
                        }
                    )

        return redirect("plant-entry")
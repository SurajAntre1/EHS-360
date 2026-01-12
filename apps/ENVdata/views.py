from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.organizations.models import Plant
from .models import MonthlyIndicatorData
from .constants import QUESTIONS, MONTHS


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

        saved_data = MonthlyIndicatorData.objects.filter(plant=plant)
        data_dict = {(d.question, d.month): d.value for d in saved_data}

        context = {
            "plant": plant,
            "questions": QUESTIONS,
            "months": MONTHS,
            "data": data_dict,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        plant = self.get_plant(request)
        if not plant:
            return redirect("plant-entry")

        for question in QUESTIONS:
            for month in MONTHS:
                field_name = f"{question}_{month}".lower() \
                    .replace(" ", "_") \
                    .replace("(", "") \
                    .replace(")", "") \
                    .replace("+", "")

                value = request.POST.get(field_name)

                if value:
                    MonthlyIndicatorData.objects.update_or_create(
                        plant=plant,
                        indicator=question,  # Changed from 'question' to 'indicator'
                        month=month.lower()[:3],  # Ensure it's lowercase 3-letter format
                        defaults={
                            "value": value,
                            "created_by": request.user
                        }
                    )

        return redirect("plant-entry")

from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.organizations.models import Plant
from .models import *
from .constants import MONTHS

from django.contrib import messages
import json



class UnitManagerView(LoginRequiredMixin, View):
    template_name = "data_collection/unit_manager.html"

    def get(self, request):
        categories = UnitCategory.objects.filter(is_active=True)
        units = Unit.objects.filter(is_active=True).select_related('category')
        return render(request, self.template_name, {
            "categories": categories,
            "units": units
        })

    def post(self, request):
        action = request.POST.get("action")

        if action == "add_category":
            name = request.POST.get("category_name").strip()
            description = request.POST.get("category_description", "").strip()
            if name:
                UnitCategory.objects.get_or_create(name=name, defaults={"description": description})
                messages.success(request, "Category added successfully")
            else:
                messages.error(request, "Category name is required")
        
        elif action == "add_unit":
            category_id = request.POST.get("category")
            name = request.POST.get("unit_name").strip()
            base_unit = request.POST.get("base_unit").strip()
            conversion_rate = request.POST.get("conversion_rate", "1").strip()

            try:
                category = UnitCategory.objects.get(id=category_id)
                conversion_rate = float(conversion_rate)
                Unit.objects.create(
                    category=category,
                    name=name,
                    base_unit=base_unit,
                    conversion_rate=conversion_rate,
                    created_by=request.user
                )
                messages.success(request, "Unit added successfully")
            except UnitCategory.DoesNotExist:
                messages.error(request, "Invalid category selected")
            except ValueError:
                messages.error(request, "Conversion rate must be a number")

        return redirect("unit-manager")

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
        'Yes/No': {'Yes/No': 1},
    }

    # ---------- HELPERS ----------

    def get_plant(self, request):
        return Plant.objects.filter(users=request.user, is_active=True).first()

    def get_questions(self):
        return EnvironmentalQuestion.objects.filter(
            is_active=True
        ).order_by('order')

    def slugify_field(self, text):
        return (
            text.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
            .replace(",", "")
            .replace(".", "")
            .replace(";", "")
            .replace("'", "")
        )

    def convert_value(self, value, from_unit, to_unit):
        if from_unit == to_unit:
            return value

        if from_unit in ['Count', 'Rate', 'Percentage', 'Yes/No'] or to_unit == 'Yes/No':
            return value

        return (
            value * self.CONVERSION_FACTORS.get(from_unit, {}).get(to_unit, 1)
        )

    # ---------- GET ----------

    def get(self, request):
        plant = self.get_plant(request)
        if not plant:
            return render(request, "no_plant_assigned.html")

        questions = self.get_questions()
        if not questions.exists():
            return render(request, self.template_name, {
                "plant": plant,
                "no_questions": True
            })

        saved_data = MonthlyIndicatorData.objects.filter(plant=plant)

        data_dict = {}
        unit_dict = {}

        for d in saved_data:
            if d.indicator not in data_dict:
                data_dict[d.indicator] = {}

            if d.indicator not in unit_dict and d.unit:
                unit_dict[d.indicator] = d.unit

            base_unit = EnvironmentalQuestion.objects.get(
                question_text=d.indicator
            ).default_unit

            stored_value = float(d.value)
            display_value = self.convert_value(
                stored_value,
                base_unit,
                unit_dict[d.indicator]
            )

            data_dict[d.indicator][d.month.capitalize()] = display_value

        # fallback default unit
        for q in questions:
            if q.question_text not in unit_dict:
                unit_dict[q.question_text] = q.default_unit

        context = {
            "plant": plant,
            "questions": [
                {
                    "question": q.question_text,
                    "default_unit": q.default_unit,
                    "unit_options": q.get_unit_options_list(),
                }
                for q in questions
            ],
            "months": MONTHS,
            "data": data_dict,
            "unit_dict": unit_dict,
        }

        return render(request, self.template_name, context)

    # ---------- POST ----------

    def post(self, request):
        plant = self.get_plant(request)
        if not plant:
            return redirect("plant-entry")

        questions = self.get_questions()

        for q in questions:
            question_text = q.question_text
            base_unit = q.default_unit

            unit_field = f"unit_{self.slugify_field(question_text)}"
            selected_unit = request.POST.get(unit_field, base_unit)

            for month in MONTHS:
                field_name = f"{self.slugify_field(question_text)}_{month.lower()}"
                value = request.POST.get(field_name, "").strip()

                if value=="":
                    continue

                try:
                    numeric_value = float(value.replace(",", ""))
                    stored_value = self.convert_value(
                        numeric_value, selected_unit, base_unit
                    )

                    MonthlyIndicatorData.objects.update_or_create(
                        plant=plant,
                        indicator=question_text,
                        month=month.lower()[:3],
                        defaults={
                            "value": str(stored_value),
                            "unit": selected_unit,
                            "created_by": request.user,
                        }
                    )
                except ValueError:
                    continue

        return redirect("plant-entry")

    



class EnvironmentalQuestionsManagerView(LoginRequiredMixin, View):
    """
    View to manage environmental questions - Add, Edit, Delete, Reorder
    """
    template_name = "data_collection/questions_manager.html"

    # ---------- GET ----------

    def get(self, request):
        questions = self.load_questions()
        return render(request, self.template_name, {"questions": questions})

    # ---------- POST ROUTER ----------

    def post(self, request):
        action = request.POST.get("action")

        actions = {
            "add": self.add_question,
            "delete": self.delete_question,
            "reorder": self.reorder_questions,
            "save_all": self.save_all_questions,
        }

        if action in actions:
            return actions[action](request)

        return redirect("questions-manager")

    # ---------- HELPERS ----------

    def load_questions(self):
        """
        Load questions ONLY from database
        """
        return [
            {
                "id": q.id,
                "question": q.question_text,
                "default_unit": q.default_unit,
                "unit_options": q.get_unit_options_list(),
                "order": q.order,
            }
            for q in EnvironmentalQuestion.objects.filter(
                is_active=True
            ).order_by("order")
        ]

    # ---------- ACTIONS ----------

    def add_question(self, request):
        question_text = request.POST.get("question_text", "").strip()
        default_unit = request.POST.get("default_unit", "Count").strip()
        unit_options = request.POST.get("unit_options", default_unit).strip()

        if not question_text:
            messages.error(request, "Question text is required")
            return redirect("questions-manager")

        # Prevent duplicates
        if EnvironmentalQuestion.objects.filter(
            question_text__iexact=question_text,
            is_active=True
        ).exists():
            messages.error(request, "This question already exists")
            return redirect("questions-manager")

        max_order = (
            EnvironmentalQuestion.objects.aggregate(
                max_order=models.Max("order")
            )["max_order"]
            or 0
        )

        EnvironmentalQuestion.objects.create(
            question_text=question_text,
            default_unit=default_unit,
            unit_options=unit_options,
            order=max_order + 1,
            created_by=request.user,
            is_active=True,
        )

        messages.success(request, "Question added successfully")
        return redirect("questions-manager")

    def delete_question(self, request):
        question_id = request.POST.get("question_id")

        try:
            question = EnvironmentalQuestion.objects.get(id=question_id)
            question.is_active = False
            question.save(update_fields=["is_active"])

            messages.success(request, "Question deleted successfully")
        except EnvironmentalQuestion.DoesNotExist:
            messages.error(request, "Question not found")

        return redirect("questions-manager")

    def reorder_questions(self, request):
        """
        Expected JSON:
        [
            {"id": 1, "order": 1},
            {"id": 2, "order": 2}
        ]
        """
        order_data = request.POST.get("order_data")

        try:
            orders = json.loads(order_data)
            for item in orders:
                EnvironmentalQuestion.objects.filter(
                    id=item["id"]
                ).update(order=item["order"])

            messages.success(request, "Questions reordered successfully")
        except Exception:
            messages.error(request, "Failed to reorder questions")

        return redirect("questions-manager")

    def save_all_questions(self, request):
        """
        Save all questions from editable list
        """
        question_count = int(request.POST.get("question_count", 0))

        for i in range(question_count):
            question_id = request.POST.get(f"question_id_{i}")
            question_text = request.POST.get(f"question_text_{i}", "").strip()
            default_unit = request.POST.get(f"default_unit_{i}", "Count").strip()
            unit_options = request.POST.get(
                f"unit_options_{i}", default_unit
            ).strip()

            if not question_text:
                continue

            if question_id:
                EnvironmentalQuestion.objects.filter(id=question_id).update(
                    question_text=question_text,
                    default_unit=default_unit,
                    unit_options=unit_options,
                    order=i + 1,
                )
            else:
                EnvironmentalQuestion.objects.create(
                    question_text=question_text,
                    default_unit=default_unit,
                    unit_options=unit_options,
                    order=i + 1,
                    created_by=request.user,
                    is_active=True,
                )

        messages.success(request, "All questions saved successfully")
        return redirect("questions-manager")

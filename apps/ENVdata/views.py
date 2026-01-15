from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import models
from django.http import JsonResponse

from apps.organizations.models import Plant
from .models import *
from .constants import MONTHS


# =========================================================
# UNIT MANAGER
# =========================================================

class UnitManagerView(LoginRequiredMixin, View):
    template_name = "data_collection/unit_manager.html"

    def get(self, request):
        categories = UnitCategory.objects.filter(is_active=True)
        units = Unit.objects.filter(is_active=True).select_related("category")

        return render(request, self.template_name, {
            "categories": categories,
            "units": units,
        })

    def post(self, request):
        action = request.POST.get("action")

        # ---------- CREATE CATEGORY ----------
        if action == "create_category":
            name = (request.POST.get("category_name") or "").strip()
            description = (request.POST.get("category_description") or "").strip()
            is_active = request.POST.get("category_is_active") == "on"

            if not name:
                messages.error(request, "Category name is required")
                return redirect("environmental:unit-manager")

            UnitCategory.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "is_active": is_active,
                    "created_by": request.user,
                }
            )

            messages.success(request, "Category added successfully")
            return redirect("environmental:unit-manager")

        # ---------- CREATE UNIT ----------
        elif action == "create_unit":
            category_id = request.POST.get("unit_category")
            name = (request.POST.get("unit_name") or "").strip()
            base_unit = (request.POST.get("unit_base_unit") or "").strip()
            conversion_rate = request.POST.get("unit_conversion_rate")
            is_active = request.POST.get("unit_is_active") == "on"

            if not all([category_id, name, base_unit, conversion_rate]):
                messages.error(request, "All unit fields are required")
                return redirect("environmental:unit-manager")

            try:
                category = UnitCategory.objects.get(id=category_id)
                conversion_rate = float(conversion_rate)

                if conversion_rate <= 0:
                    raise ValueError

                Unit.objects.create(
                    category=category,
                    name=name,
                    base_unit=base_unit,
                    conversion_rate=conversion_rate,
                    is_active=is_active,
                    created_by=request.user,
                )

                messages.success(request, "Unit added successfully")

            except UnitCategory.DoesNotExist:
                messages.error(request, "Invalid category selected")
            except ValueError:
                messages.error(request, "Conversion rate must be a number greater than 0")

            return redirect("environmental:unit-manager")

        return redirect("environmental:unit-manager")


# =========================================================
# PLANT MONTHLY ENTRY
# =========================================================

class PlantMonthlyEntryView(LoginRequiredMixin, View):
    template_name = "data_collection/data_env.html"

    # ---------- HELPERS ----------

    def get_plant(self, request):
        return Plant.objects.filter(users=request.user, is_active=True).first()

    def get_questions(self):
        return EnvironmentalQuestion.objects.filter(
            is_active=True
        ).select_related('unit_category', 'default_unit').prefetch_related('selected_units').order_by("order")

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

    # ---------- GET ----------

    def get(self, request):
        plant = self.get_plant(request)
        if not plant:
            return render(request, "no_plant_assigned.html")

        questions = self.get_questions()
        if not questions.exists():
            return render(request, self.template_name, {
                "plant": plant,
                "no_questions": True,
            })

        saved_data = MonthlyIndicatorData.objects.filter(plant=plant)

        data_dict = {}
        unit_dict = {}

        for d in saved_data:
            data_dict.setdefault(d.indicator, {})
            if d.indicator not in unit_dict and d.unit:
                unit_dict[d.indicator] = d.unit
            data_dict[d.indicator][d.month.capitalize()] = d.value

        # Build questions list with unit information
        questions_list = []
        for q in questions:
            default_unit_name = q.default_unit.name if q.default_unit else "Count"
            
            questions_list.append({
                "question": q.question_text,
                "default_unit": default_unit_name,
                "default_unit_name": default_unit_name,
            })

        context = {
            "plant": plant,
            "questions": questions_list,
            "months": MONTHS,
            "data": data_dict,
            "unit_dict": unit_dict,
        }

        return render(request, self.template_name, context)

    # ---------- POST ----------

    def post(self, request):
        plant = self.get_plant(request)
        if not plant:
            return redirect("environmental:plant-entry")

        questions = self.get_questions()

        for q in questions:
            question_text = q.question_text
            default_unit = q.default_unit.name if q.default_unit else "Count"

            for month in MONTHS:
                field_name = f"{self.slugify_field(question_text)}_{month.lower()}"
                value = (request.POST.get(field_name) or "").strip()

                if not value:
                    continue

                try:
                    numeric_value = float(value.replace(",", ""))

                    MonthlyIndicatorData.objects.update_or_create(
                        plant=plant,
                        indicator=question_text,
                        month=month.lower()[:3],
                        defaults={
                            "value": str(numeric_value),
                            "unit": default_unit,
                            "created_by": request.user,
                        }
                    )
                except ValueError:
                    continue

        messages.success(request, "Data saved successfully!")
        return redirect("environmental:plant-entry")


# =========================================================
# QUESTIONS MANAGER
# =========================================================

class EnvironmentalQuestionsManagerView(LoginRequiredMixin, View):
    template_name = "data_collection/questions_manager.html"

    def get(self, request):
        categories = UnitCategory.objects.filter(is_active=True)
        
        return render(request, self.template_name, {
            "questions": self.load_questions(),
            "categories": categories
        })

    def post(self, request):
        action = request.POST.get("action")

        actions = {
            "add": self.add_question,
            "delete": self.delete_question,
        }

        return actions.get(action, lambda r: redirect(
            "environmental:questions-manager"
        ))(request)

    def load_questions(self):
        questions_list = []
        for q in EnvironmentalQuestion.objects.filter(is_active=True).order_by("order"):
            selected_units = q.selected_units.all()
            questions_list.append({
                "id": q.id,
                "question": q.question_text,
                "category_id": q.unit_category.id if q.unit_category else None,
                "category_name": q.unit_category.name if q.unit_category else "Not Set",
                "default_unit_id": q.default_unit.id if q.default_unit else None,
                "default_unit_name": q.default_unit.name if q.default_unit else "Not Set",
                "selected_unit_ids": [u.id for u in selected_units],
                "selected_unit_names": [u.name for u in selected_units],
                "order": q.order,
            })
        return questions_list

    def add_question(self, request):
        question_text = (request.POST.get("question_text") or "").strip()
        category_id = request.POST.get("category_id")
        default_unit_id = request.POST.get("default_unit_id")
        selected_unit_ids = request.POST.getlist("selected_unit_ids[]")

        # Validation
        if not question_text or not category_id:
            messages.error(request, "Question text and category are required")
            return redirect("environmental:questions-manager")

        if EnvironmentalQuestion.objects.filter(
            question_text__iexact=question_text,
            is_active=True
        ).exists():
            messages.error(request, "This question already exists")
            return redirect("environmental:questions-manager")

        if not selected_unit_ids:
            messages.error(request, "Please select at least one unit")
            return redirect("environmental:questions-manager")

        if not default_unit_id:
            messages.error(request, "Please select a default unit")
            return redirect("environmental:questions-manager")

        if default_unit_id not in selected_unit_ids:
            messages.error(request, "Default unit must be one of the selected units")
            return redirect("environmental:questions-manager")

        # Create question
        max_order = EnvironmentalQuestion.objects.aggregate(
            max=models.Max("order")
        )["max"] or 0

        question = EnvironmentalQuestion.objects.create(
            question_text=question_text,
            unit_category_id=category_id,
            default_unit_id=default_unit_id,
            order=max_order + 1,
            created_by=request.user,
            is_active=True,
        )
        
        # Add selected units
        question.selected_units.set(selected_unit_ids)

        messages.success(request, "Question added successfully")
        return redirect("environmental:questions-manager")

    def delete_question(self, request):
        question_id = request.POST.get("question_id")

        if not question_id:
            messages.error(request, "Question ID is required")
            return redirect("environmental:questions-manager")

        deleted_count = EnvironmentalQuestion.objects.filter(
            id=question_id
        ).update(is_active=False)

        if deleted_count > 0:
            messages.success(request, "Question deleted successfully")
        else:
            messages.error(request, "Question not found")

        return redirect("environmental:questions-manager")


# =========================================================
# API ENDPOINT FOR FETCHING UNITS BY CATEGORY
# =========================================================

class GetCategoryUnitsAPIView(LoginRequiredMixin, View):
    """
    API endpoint to fetch units for a selected category
    """
    def get(self, request):
        category_id = request.GET.get('category_id')
        
        if not category_id:
            return JsonResponse({
                'success': False,
                'error': 'Category ID is required'
            }, status=400)
        
        try:
            # Fetch units for the category
            units = Unit.objects.filter(
                category_id=category_id,
                is_active=True
            ).values('id', 'name', 'base_unit', 'conversion_rate').order_by('name')
            
            return JsonResponse({
                'success': True,
                'units': list(units)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
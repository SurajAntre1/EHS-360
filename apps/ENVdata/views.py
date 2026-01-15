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

    def get_user_plants(self, request):
        """Get all plants assigned to the user"""
        user = request.user
        
        # Admin/Superuser can access all plants
        if user.is_superuser or user.is_staff or user.is_admin_user:
            return Plant.objects.filter(is_active=True).order_by('name')
        
        # Get user's assigned plants (using ManyToMany field)
        assigned = user.assigned_plants.filter(is_active=True)
        
        # If no assigned plants, check primary plant
        if not assigned.exists() and user.plant:
            return Plant.objects.filter(id=user.plant.id, is_active=True)
        
        return assigned.order_by('name')

    def get_selected_plant(self, request):
        """Get the currently selected plant"""
        plant_id = request.GET.get('plant_id') or request.POST.get('selected_plant_id')
        
        if plant_id:
            user_plants = self.get_user_plants(request)
            return user_plants.filter(id=plant_id).first()
        
        # Return first assigned plant by default
        return self.get_user_plants(request).first()

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
        user_plants = self.get_user_plants(request)
        
        # Check if user has any plants assigned
        if not user_plants.exists():
            return render(request, "no_plant_assigned.html")
        
        # Get the selected plant
        selected_plant = self.get_selected_plant(request)
        
        if not selected_plant:
            return render(request, "no_plant_assigned.html")

        # Get all questions
        questions = self.get_questions()
        
        if not questions.exists():
            return render(request, self.template_name, {
                "selected_plant": selected_plant,
                "user_plants": user_plants,
                "no_questions": True,
            })

        # Get saved data for the SELECTED plant only
        saved_data = MonthlyIndicatorData.objects.filter(plant=selected_plant)

        # Organize data by question and month
        data_dict = {}
        for d in saved_data:
            if d.indicator not in data_dict:
                data_dict[d.indicator] = {}
            data_dict[d.indicator][d.month.lower()] = d.value

        # Build questions list with their data for the selected plant
        questions_with_data = []
        for q in questions:
            default_unit_name = q.default_unit.name if q.default_unit else "Count"
            
            # Get data for each month for this question
            month_data = {}
            for month in MONTHS:
                month_key = month.lower()[:3]
                value = data_dict.get(q.question_text, {}).get(month_key, '')
                month_data[month] = value
            
            questions_with_data.append({
                "question": q.question_text,
                "default_unit": default_unit_name,
                "default_unit_name": default_unit_name,
                "month_data": month_data,
                "slugified": self.slugify_field(q.question_text),
            })

        context = {
            "selected_plant": selected_plant,
            "user_plants": user_plants,
            "questions_with_data": questions_with_data,
            "months": MONTHS,
        }

        return render(request, self.template_name, context)

    # ---------- POST ----------

    def post(self, request):
        # Get the selected plant from the form
        selected_plant_id = request.POST.get('selected_plant_id')
        
        if not selected_plant_id:
            messages.error(request, "Please select a plant")
            return redirect("environmental:plant-entry")
        
        user_plants = self.get_user_plants(request)
        selected_plant = user_plants.filter(id=selected_plant_id).first()
        
        if not selected_plant:
            messages.error(request, "Invalid plant selected")
            return redirect("environmental:plant-entry")

        questions = self.get_questions()

        # Save data for the selected plant
        for q in questions:
            question_text = q.question_text
            default_unit = q.default_unit.name if q.default_unit else "Count"

            for month in MONTHS:
                field_name = f"{self.slugify_field(question_text)}_{month.lower()}"
                value = (request.POST.get(field_name) or "").strip()

                if not value:
                    # Delete if exists and now empty
                    MonthlyIndicatorData.objects.filter(
                        plant=selected_plant,
                        indicator=question_text,
                        month=month.lower()[:3]
                    ).delete()
                    continue

                try:
                    numeric_value = float(value.replace(",", ""))

                    MonthlyIndicatorData.objects.update_or_create(
                        plant=selected_plant,
                        indicator=question_text,
                        month=month.lower()[:3],
                        defaults={
                            "value": str(numeric_value),
                            "unit": default_unit,
                            "created_by": request.user,
                        }
                    )
                except ValueError:
                    messages.warning(request, f"Invalid value for {question_text} in {month}")
                    continue

        messages.success(request, f"Data saved successfully for {selected_plant.name}!")

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
                    # Delete if exists and now empty
                    MonthlyIndicatorData.objects.filter(
                        plant=plant,
                        indicator=question_text,
                        month=month.lower()[:3]
                    ).delete()
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

        messages.success(request, f"Data saved successfully for {plant.name}!")
        return redirect(f"{request.path}?plant_id={plant.id}")


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
        


# =========================================================
# VIEW SUBMITTED DATA - USER VIEW (Read-only)
# =========================================================

class PlantDataDisplayView(LoginRequiredMixin, View):
    template_name = "data_collection/data_display.html"

    def get_user_plants(self, request):
        """Get all plants assigned to the user"""
        user = request.user
        
        if user.is_superuser or user.is_staff or user.is_admin_user:
            return Plant.objects.filter(is_active=True)
        
        assigned = user.assigned_plants.filter(is_active=True)
        
        if not assigned.exists() and user.plant:
            return Plant.objects.filter(id=user.plant.id, is_active=True)
        
        return assigned

    def get(self, request):
        plant_id = request.GET.get('plant_id')
        user_plants = self.get_user_plants(request)
        
        if plant_id:
            plant = user_plants.filter(id=plant_id).first()
        else:
            plant = user_plants.first()
        
        if not plant:
            return render(request, "no_plant_assigned.html")

        questions = EnvironmentalQuestion.objects.filter(
            is_active=True
        ).select_related('unit_category', 'default_unit').order_by("order")

        if not questions.exists():
            return render(request, self.template_name, {
                "plant": plant,
                "user_plants": user_plants,
                "no_questions": True,
            })

        # Get saved data for this plant
        saved_data = MonthlyIndicatorData.objects.filter(plant=plant)

        # Organize data
        data_dict = {}
        for d in saved_data:
            if d.indicator not in data_dict:
                data_dict[d.indicator] = {}
            data_dict[d.indicator][d.month.lower()] = d.value

        # Build display structure
        questions_data = []
        for q in questions:
            default_unit_name = q.default_unit.name if q.default_unit else "Count"
            
            month_data = {}
            total = 0
            has_values = False
            
            for month in MONTHS:
                month_key = month.lower()[:3]
                value = data_dict.get(q.question_text, {}).get(month_key, '')
                month_data[month] = value
                
                if value:
                    try:
                        total += float(str(value).replace(',', ''))
                        has_values = True
                    except (ValueError, TypeError):
                        pass
            
            questions_data.append({
                "question": q.question_text,
                "unit": default_unit_name,
                "month_data": month_data,
                "annual": f"{total:,.2f}" if has_values else '',
            })

        context = {
            "plant": plant,
            "user_plants": user_plants,
            "questions_data": questions_data,
            "months": MONTHS,
        }

        return render(request, self.template_name, context)


# =========================================================
# ADMIN VIEW - ALL PLANTS DATA
# =========================================================

class AdminAllPlantsDataView(LoginRequiredMixin, View):
    template_name = "data_collection/admin_all_plants.html"

    def get(self, request):
        # Check if user is admin/superuser
        if not (request.user.is_superuser or request.user.is_staff or request.user.is_admin_user):
            messages.error(request, "You don't have permission to access this page")
            return redirect("environmental:plant-entry")

        # Get ALL active plants (no user filtering)
        all_plants = Plant.objects.filter(is_active=True).order_by('name')

        if not all_plants.exists():
            return render(request, self.template_name, {
                "no_plants": True,
            })

        # Get all questions (ordered)
        questions = EnvironmentalQuestion.objects.filter(
            is_active=True
        ).select_related('unit_category', 'default_unit').order_by("order")

        if not questions.exists():
            return render(request, self.template_name, {
                "no_questions": True,
            })

        # Get ALL saved data efficiently
        all_data = MonthlyIndicatorData.objects.select_related('plant').all()

        # Build data structure: list of plants with their question data
        plants_data = []
        plants_with_data_count = 0
        
        for plant in all_plants:
            plant_questions_data = []
            plant_has_any_data = False
            
            # For each question, get this plant's data
            for q in questions:
                default_unit_name = q.default_unit.name if q.default_unit else "Count"
                
                # Collect monthly data for this plant + question
                month_data = {}
                total = 0
                has_values = False
                
                for month in MONTHS:
                    month_key = month.lower()[:3]  # jan, feb, mar
                    
                    # Find the specific data entry
                    data_entry = all_data.filter(
                        plant=plant,
                        indicator=q.question_text,
                        month=month_key
                    ).first()
                    
                    if data_entry and data_entry.value:
                        value = data_entry.value
                        plant_has_any_data = True
                        month_data[month] = value
                        
                        # Calculate total for annual
                        try:
                            numeric_value = float(str(value).replace(',', ''))
                            total += numeric_value
                            has_values = True
                        except (ValueError, TypeError):
                            pass
                    else:
                        month_data[month] = ''
                
                # Format annual total
                annual_display = f"{total:,.2f}" if has_values else "0%"
                
                # Add question data for this plant
                plant_questions_data.append({
                    "question": q.question_text,
                    "unit": default_unit_name,
                    "month_data": month_data,
                    "annual": annual_display,
                    "has_data": has_values,
                })
            
            # Count plants with data
            if plant_has_any_data:
                plants_with_data_count += 1
            
            # Add this plant's complete data
            plants_data.append({
                "plant": plant,
                "questions_data": plant_questions_data,
                "has_data": plant_has_any_data,
            })

        context = {
            "plants_data": plants_data,
            "months": MONTHS,
            "total_plants": all_plants.count(),
            "plants_with_data": plants_with_data_count,
            "total_questions": questions.count(),
        }

        return render(request, self.template_name, context)
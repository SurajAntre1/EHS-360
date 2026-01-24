from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.http import HttpResponse
from datetime import datetime
from django.core.paginator import Paginator 
from apps.accounts.models import User
from apps.accidents.models import Incident
from apps.organizations.models import Plant
from .models import *
from .utils import EnvironmentalDataFetcher


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

    def get_user_plants(self, request):
        user = request.user
        if user.is_superuser or user.is_staff or getattr(user, 'is_admin_user', False):
            return Plant.objects.filter(is_active=True).order_by('name')

        assigned = user.assigned_plants.filter(is_active=True)
        if not assigned.exists() and getattr(user, 'plant', None):
            return Plant.objects.filter(id=user.plant.id, is_active=True)

        return assigned.order_by('name')

    def get_selected_plant(self, request):
        plant_id = request.GET.get('plant_id') or request.POST.get('selected_plant_id')
        if plant_id:
            return self.get_user_plants(request).filter(id=plant_id).first()
        return self.get_user_plants(request).first()

    def get_questions(self):
        return EnvironmentalQuestion.objects.filter(
            is_active=True
        ).select_related('unit_category', 'default_unit').prefetch_related('selected_units').order_by("is_system", "order", "id")

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

    def get(self, request):
        user_plants = self.get_user_plants(request)
        if not user_plants.exists():
            return render(request, "no_plant_assigned.html")

        selected_plant = self.get_selected_plant(request)
        if not selected_plant:
            return render(request, "no_plant_assigned.html")

        questions = self.get_questions()
        if not questions.exists():
            return render(request, self.template_name, {
                "selected_plant": selected_plant,
                "user_plants": user_plants,
                "no_questions": True,
            })

        current_year = datetime.now().year

        # Get auto-populated data
        auto_data = EnvironmentalDataFetcher.get_data_for_plant_year(selected_plant, current_year)

        # Fetch saved monthly data
        saved_data = MonthlyIndicatorData.objects.filter(
            plant=selected_plant
        ).select_related('indicator')
        
        saved_dict = {}
        for d in saved_data:
            if d.indicator not in saved_dict:
                saved_dict[d.indicator] = {}
            saved_dict[d.indicator][d.month.lower()] = d.value

        MONTHS = MonthlyIndicatorData.MONTH_CHOICES

        # Build question + month data for template
        questions_with_data = []
        for q in questions:
            default_unit_name = q.default_unit.name if q.default_unit else "Count"
            
            # Check if this question has auto-calculation
            is_auto = q.question_text in auto_data

            month_rows = []
            for month_code, month_name in MONTHS:
                value = ''
                key = month_code.lower()
                
                # Priority 1: Check saved manual data
                if q in saved_dict and key in saved_dict[q]:
                    value = saved_dict[q][key]
                # Priority 2: Check auto-calculated data
                elif is_auto and month_name in auto_data.get(q.question_text, {}):
                    value = auto_data[q.question_text][month_name]

                month_rows.append({
                    "code": month_code,
                    "name": month_name,
                    "value": value,
                })

            questions_with_data.append({
                "question": q.question_text,
                "question_id": q.id,
                "default_unit_name": default_unit_name,
                "months": month_rows,
                "slugified": self.slugify_field(q.question_text),
                "is_auto_populated": is_auto,
                "source_type": q.source_type,
            })

        auto_count = sum(1 for q in questions_with_data if q['is_auto_populated'])
        manual_count = len(questions_with_data) - auto_count

        context = {
            "selected_plant": selected_plant,
            "user_plants": user_plants,
            "questions_with_data": questions_with_data,
            "months": MONTHS,
            "current_year": current_year,
            "total_questions": len(questions_with_data),
            "auto_populated_count": auto_count,
            "manual_entry_count": manual_count,
        }

        return render(request, self.template_name, context)

    def post(self, request):
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
        MONTHS = MonthlyIndicatorData.MONTH_CHOICES

        for q in questions:
            default_unit = q.default_unit.name if q.default_unit else "Count"
            slug = self.slugify_field(q.question_text)

            for month_code, month_name in MONTHS:
                field_name = f"{slug}_{month_code.lower()}"
                value = (request.POST.get(field_name) or "").strip()

                if not value:
                    MonthlyIndicatorData.objects.filter(
                        plant=selected_plant,
                        indicator=q,
                        month=month_code
                    ).delete()
                    continue

                try:
                    numeric_value = float(value.replace(",", ""))
                    MonthlyIndicatorData.objects.update_or_create(
                        plant=selected_plant,
                        indicator=q,
                        month=month_code,
                        defaults={
                            "value": str(numeric_value),
                            "unit": default_unit,
                            "created_by": request.user,
                        }
                    )
                except ValueError:
                    messages.warning(request, f"Invalid value for {q.question_text} in {month_name}")

        messages.success(request, f"Data saved successfully for {selected_plant.name}!")
        return redirect(f"{request.path}?plant_id={selected_plant.id}&saved=1")


# =========================================================
# QUESTIONS MANAGER
# =========================================================

class EnvironmentalQuestionsManagerView(LoginRequiredMixin, View):
    template_name = "data_collection/questions_manager.html"

    def get(self, request):
        categories = UnitCategory.objects.filter(is_active=True)
        selected_category_id = request.GET.get('category_id')
        
        units = []
        if selected_category_id:
            units = Unit.objects.filter(
                category_id=selected_category_id,
                is_active=True
            ).order_by('name')
        
        return render(request, self.template_name, {
            "questions": self.load_questions(),
            "categories": categories,
            "selected_category_id": selected_category_id,
            "units": units,
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
        for q in EnvironmentalQuestion.objects.filter(is_active=True).order_by("is_system", "order", "id"):
            selected_units = q.selected_units.all()
            
            # Build filter description
            filter_desc = ""
            if q.filter_field and q.filter_value:
                filter_desc = f"{q.filter_field} = {q.filter_value}"
                if q.filter_field_2 and q.filter_value_2:
                    filter_desc += f" AND {q.filter_field_2} = {q.filter_value_2}"
            
            questions_list.append({
                "id": q.id,
                "question": q.question_text,
                "category_id": q.unit_category.id if q.unit_category else None,
                "category_name": q.unit_category.name if q.unit_category else "Not Set",
                "default_unit_id": q.default_unit.id if q.default_unit else None,
                "default_unit_name": q.default_unit.name if q.default_unit else "Count",
                "selected_unit_ids": [u.id for u in selected_units],
                "selected_unit_names": [u.name for u in selected_units],
                "order": q.order,
                "source_type": q.source_type,
                "filter_description": filter_desc,
            })
        return questions_list

    def add_question(self, request):
        question_text = (request.POST.get("question_text") or "").strip()
        category_id = request.POST.get("category_id")
        default_unit_id = request.POST.get("default_unit_id")
        selected_unit_ids = request.POST.getlist("selected_unit_ids[]")
        source_type = request.POST.get("source_type", "MANUAL")
        
        # Dynamic filter fields
        filter_field = (request.POST.get("filter_field") or "").strip()
        filter_value = (request.POST.get("filter_value") or "").strip()
        filter_field_2 = (request.POST.get("filter_field_2") or "").strip()
        filter_value_2 = (request.POST.get("filter_value_2") or "").strip()
        
        # Validation
        if not question_text:
            messages.error(request, "Question text is required")
            return redirect("environmental:questions-manager")

        if EnvironmentalQuestion.objects.filter(
            question_text__iexact=question_text,
            is_active=True
        ).exists():
            messages.error(request, "This question already exists")
            return redirect("environmental:questions-manager")

        # For auto-calculated questions
        if source_type != 'MANUAL':
            if not filter_field or not filter_value:
                messages.error(request, "Primary filter field and value are required")
                return redirect("environmental:questions-manager")
        else:
            # Manual entry requires units
            if not category_id or not default_unit_id or not selected_unit_ids:
                messages.error(request, "Category and units are required for manual entry questions")
                return redirect(f"environmental:questions-manager?category_id={category_id}")
            
            if default_unit_id not in selected_unit_ids:
                messages.error(request, "Default unit must be one of the selected units")
                return redirect(f"environmental:questions-manager?category_id={category_id}")

        # Create question
        max_order = EnvironmentalQuestion.objects.aggregate(
            max=models.Max("order")
        )["max"] or 0

        question = EnvironmentalQuestion.objects.create(
            question_text=question_text,
            unit_category_id=category_id if category_id else None,
            default_unit_id=default_unit_id if default_unit_id else None,
            source_type=source_type,
            filter_field=filter_field if filter_field else None,
            filter_value=filter_value if filter_value else None,
            filter_field_2=filter_field_2 if filter_field_2 else None,
            filter_value_2=filter_value_2 if filter_value_2 else None,
            order=max_order + 1,
            created_by=request.user,
            is_active=True,
            is_system=False,
        )
        
        # Add selected units if provided
        if selected_unit_ids:
            question.selected_units.set(selected_unit_ids)

        messages.success(request, "Question added successfully")
        return redirect("environmental:questions-manager")

    def delete_question(self, request):
        question_id = request.POST.get("question_id")

        question = EnvironmentalQuestion.objects.filter(id=question_id).first()

        if not question:
            messages.error(request, "Question not found")
            return redirect("environmental:questions-manager")

        if question.is_system:
            messages.error(request, "Predefined questions cannot be deleted")
            return redirect("environmental:questions-manager")

        question.is_active = False
        question.save()

        messages.success(request, "Question deleted successfully")
        return redirect("environmental:questions-manager")


# =========================================================
# API ENDPOINTS
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


class GetSourceFieldsAPIView(LoginRequiredMixin, View):
    """
    API to get available fields and their choices for a source type
    """
    def get(self, request):
        source_type = request.GET.get('source_type')
        
        if not source_type:
            return JsonResponse({
                'success': False,
                'error': 'Source type is required'
            }, status=400)
        
        try:
            from apps.accidents.models import Incident
            from apps.hazards.models import Hazard
            
            # Get model based on source type
            if source_type == 'INCIDENT':
                model = Incident
            elif source_type == 'HAZARD':
                model = Hazard
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid source type'
                }, status=400)
            
            # Get fields with choices
            fields_with_choices = []
            
            for field in model._meta.get_fields():
                if hasattr(field, 'choices') and field.choices:
                    choices = [{'value': choice[0], 'display': choice[1]} for choice in field.choices]
                    fields_with_choices.append({
                        'field_name': field.name,
                        'field_verbose_name': field.verbose_name.title(),
                        'choices': choices
                    })
            
            return JsonResponse({
                'success': True,
                'fields': fields_with_choices
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
        
        if user.is_superuser or user.is_staff or getattr(user, 'is_admin_user', False):
            return Plant.objects.filter(is_active=True)
        
        assigned = user.assigned_plants.filter(is_active=True)
        
        if not assigned.exists() and getattr(user, 'plant', None):
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
        ).select_related('unit_category', 'default_unit').order_by("is_system", "order", "id")

        if not questions.exists():
            return render(request, self.template_name, {
                "plant": plant,
                "user_plants": user_plants,
                "no_questions": True,
            })

        # Get saved data for this plant - FILTER OUT NULL indicators
        saved_data = MonthlyIndicatorData.objects.filter(
            plant=plant,
            indicator__isnull=False
        ).select_related('indicator')

        # Organize data by question
        data_dict = {}
        for d in saved_data:
            if d.indicator is None:
                continue
                
            if d.indicator not in data_dict:
                data_dict[d.indicator] = {}
            data_dict[d.indicator][d.month.lower()] = d.value

        MONTHS = MonthlyIndicatorData.MONTH_CHOICES

        # Build display structure
        questions_data = []
        for q in questions:
            default_unit_name = q.default_unit.name if q.default_unit else "Count"
            
            # Create a list of month values in order
            month_values = []
            total = 0
            has_values = False
            
            for month_code, month_name in MONTHS:
                month_key = month_code.lower()
                value = data_dict.get(q, {}).get(month_key, '')
                
                # Store the value
                month_values.append(value if value else '-')
                
                # Calculate total
                if value:
                    try:
                        total += float(str(value).replace(',', ''))
                        has_values = True
                    except (ValueError, TypeError):
                        pass
            
            questions_data.append({
                "question": q.question_text,
                "unit": default_unit_name,
                "month_values": month_values,  # List of values in order
                "annual": f"{total:,.2f}" if has_values else '-',
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

from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator

class AdminAllPlantsDataView(LoginRequiredMixin, View):
    template_name = "data_collection/admin_all_plants.html"

    def get(self, request):
        # Permission check
        if not (request.user.is_superuser or request.user.is_staff or getattr(request.user, 'is_admin_user', False)):
            messages.error(request, "You don't have permission to access this page")
            return redirect("environmental:plant-entry")

        # ALL plants
        all_plants = Plant.objects.filter(is_active=True).order_by("name")

        if not all_plants.exists():
            return render(request, self.template_name, {"no_plants": True})

        # ✅ PAGINATION — ONE PLANT ONLY
        paginator = Paginator(all_plants, 1)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Questions
        questions = EnvironmentalQuestion.objects.filter(
            is_active=True
        ).select_related(
            "unit_category", "default_unit"
        ).order_by("is_system", "order", "id")

        if not questions.exists():
            return render(request, self.template_name, {"no_questions": True})

        # ALL indicator data (queried once)
        all_data = MonthlyIndicatorData.objects.filter(
            indicator__isnull=False
        ).select_related("plant", "indicator")

        MONTHS = MonthlyIndicatorData.MONTH_CHOICES

        plants_data = []

        # 🔥 THIS IS THE FIX — page_obj, NOT all_plants
        for plant in page_obj:
            plant_questions_data = []

            for q in questions:
                unit_name = q.default_unit.name if q.default_unit else "Count"
                month_data = {}
                total = 0
                has_values = False

                for month_code, month_name in MONTHS:
                    data = all_data.filter(
                        plant=plant,
                        indicator=q,
                        month=month_code.upper()
                    ).first()

                    if data and data.value:
                        month_data[month_name] = data.value
                        try:
                            total += float(str(data.value).replace(",", ""))
                            has_values = True
                        except Exception:
                            pass
                    else:
                        month_data[month_name] = "-"

                plant_questions_data.append({
                    "question": q.question_text,
                    "unit": unit_name,
                    "month_data": month_data,
                    "annual": f"{total:,.2f}" if has_values else "-",
                })

            plants_data.append({
                "plant": plant,
                "questions_data": plant_questions_data,
            })

        context = {
            "plants_data": plants_data,  # WILL CONTAIN ONLY 1 PLANT
            "months": [m[1] for m in MONTHS],
            "page_obj": page_obj,
            "total_plants": all_plants.count(),
            "total_questions": questions.count(),
        }

        return render(request, self.template_name, context)
    
class GetCategoryBaseUnitAPIView(LoginRequiredMixin, View):
    """
    API endpoint to fetch the established base unit for a category.
    """
    def get(self, request):
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({
                'success': False, 
                'error': 'Category ID is required'
            }, status=400)
        
        try:
            # Find the first unit in this category to determine the base unit
            first_unit = Unit.objects.filter(category_id=category_id, is_active=True).first()
            
            # If a unit exists, return its base unit. Otherwise, return an empty string.
            base_unit = first_unit.base_unit if first_unit else ""
            
            return JsonResponse({
                'success': True,
                'base_unit': base_unit
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Count
from django.http import JsonResponse
from apps.accounts.views import AdminRequiredMixin
from apps.organizations.models import *
from .models import *
from .forms import *
from .utils import generate_incident_pdf
from django.http import HttpResponse
from django.db.models.functions import TruncMonth
from django.views.generic import UpdateView, TemplateView
from django.contrib import messages
from django.utils import timezone
from apps.notifications import *
import datetime
from django.db.models import Q
import json
import openpyxl

class IncidentDashboardView(LoginRequiredMixin, TemplateView):
    """Incident Management Dashboard"""
    template_name = 'accidents/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get incidents based on user role
        if self.request.user.is_superuser or self.request.user.role == 'ADMIN':
            incidents = Incident.objects.all()
        elif self.request.user.plant:
            incidents = Incident.objects.filter(plant=self.request.user.plant)
        else:
            incidents = Incident.objects.filter(reported_by=self.request.user)
        
        # Statistics
        context['total_incidents'] = incidents.count()
        context['open_incidents'] = incidents.exclude(status='CLOSED').count()
        context['this_month_incidents'] = incidents.filter(
            incident_date__month=datetime.date.today().month,
            incident_date__year=datetime.date.today().year
        ).count()
        context['investigation_pending'] = incidents.filter(
            investigation_required=True,
            investigation_completed_date__isnull=True
        ).count()
        
        # By Type
        context['lti_count'] = incidents.filter(incident_type='LTI').count()
        context['mtc_count'] = incidents.filter(incident_type='MTC').count()
        context['fa_count'] = incidents.filter(incident_type='FA').count()
        context['hlfi_count'] = incidents.filter(incident_type='HLFI').count()
        
        # Recent incidents
        context['recent_incidents'] = incidents.order_by('-reported_date')[:10]
        
        # Overdue investigations
        context['overdue_investigations'] = incidents.filter(
            investigation_required=True,
            investigation_completed_date__isnull=True,
            investigation_deadline__lt=datetime.date.today()
        )
        
        return context


class IncidentListView(LoginRequiredMixin, ListView):
    """List all incidents"""
    model = Incident
    template_name = 'accidents/incident_list.html'
    context_object_name = 'incidents'
    paginate_by = 20
    
    def get_queryset(self):
        # Base queryset based on user role
        if self.request.user.is_superuser or self.request.user.role == 'ADMIN':
            queryset = Incident.objects.all()
        elif self.request.user.plant:
            queryset = Incident.objects.filter(plant=self.request.user.plant)
        else:
            queryset = Incident.objects.filter(reported_by=self.request.user)
        
        queryset = queryset.select_related('plant', 'location', 'reported_by').order_by('-incident_date', '-incident_time')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(report_number__icontains=search) |
                Q(incident_type__icontains=search) |
                Q(affected_person_name__icontains=search)
            )
        
        # Filter by incident type
        incident_type = self.request.GET.get('incident_type')
        if incident_type:
            queryset = queryset.filter(incident_type=incident_type)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by plant
        plant = self.request.GET.get('plant')
        if plant:
            queryset = queryset.filter(plant_id=plant)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(incident_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(incident_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.organizations.models import Plant
        context['plants'] = Plant.objects.filter(is_active=True)
        context['incident_types'] = Incident.INCIDENT_TYPES
        context['status_choices'] = Incident.STATUS_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_incident_type'] = self.request.GET.get('incident_type', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_plant'] = self.request.GET.get('plant', '')
        return context


# Updated IncidentCreateView to handle unsafe acts and conditions
class IncidentCreateView(LoginRequiredMixin, CreateView):
    model = Incident
    form_class = IncidentReportForm
    template_name = 'accidents/incident_create.html'
    success_url = reverse_lazy('accidents:incident_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add departments
        from apps.organizations.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
        # Add employees for affected person dropdown - FIXED QUERY
        context['employees'] = User.objects.filter(
            is_active=True
        ).select_related('department').order_by('first_name', 'last_name')
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        if self.request.POST:
            # Update zone queryset based on selected plant
            plant_id = self.request.POST.get('plant')
            if plant_id:
                form.fields['zone'].queryset = Zone.objects.filter(plant_id=plant_id, is_active=True)
            
            # Update location queryset based on selected zone
            zone_id = self.request.POST.get('zone')
            if zone_id:
                form.fields['location'].queryset = Location.objects.filter(zone_id=zone_id, is_active=True)
            
            # Update sublocation queryset based on selected location
            location_id = self.request.POST.get('location')
            if location_id:
                form.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location_id=location_id, 
                    is_active=True
                )
            else:
                form.fields['sublocation'].queryset = SubLocation.objects.none()
        else:
            # For GET request, if user has location, populate sublocation options
            if self.request.user.location:
                form.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location=self.request.user.location,
                    is_active=True
                )
        
        return form
    
    def form_valid(self, form):
        # Set reported_by to current user
        form.instance.reported_by = self.request.user
        
        # Handle affected person selection
        affected_person_id = self.request.POST.get('affected_person_id', '').strip()
        if affected_person_id:
            try:
                affected_employee = User.objects.select_related('department').get(
                    id=affected_person_id,
                    is_active=True
                )
                form.instance.affected_person = affected_employee
                form.instance.affected_person_name = affected_employee.get_full_name()
                form.instance.affected_person_employee_id = affected_employee.employee_id or ''
                form.instance.affected_person_department = affected_employee.department
            except (User.DoesNotExist, ValueError):
                pass
        
        # Handle affected body parts JSON
        affected_body_parts_json = self.request.POST.get('affected_body_parts_json', '[]')
        try:
            form.instance.affected_body_parts = json.loads(affected_body_parts_json)
        except:
            form.instance.affected_body_parts = []
        
        # Handle unsafe acts JSON
        unsafe_acts_json = self.request.POST.get('unsafe_acts_json', '[]')
        try:
            form.instance.unsafe_acts = json.loads(unsafe_acts_json)
        except:
            form.instance.unsafe_acts = []
        
        # Handle unsafe acts other explanation
        form.instance.unsafe_acts_other = self.request.POST.get('unsafe_acts_other', '').strip()
        
        # Handle unsafe conditions JSON
        unsafe_conditions_json = self.request.POST.get('unsafe_conditions_json', '[]')
        try:
            form.instance.unsafe_conditions = json.loads(unsafe_conditions_json)
        except:
            form.instance.unsafe_conditions = []
        
        # Handle unsafe conditions other explanation
        form.instance.unsafe_conditions_other = self.request.POST.get('unsafe_conditions_other', '').strip()
        
        # Save the incident - IMPORTANT: This creates self.object
        response = super().form_valid(form)
        
        # Handle photo uploads
        photos = self.request.FILES.getlist('photos')
        for photo in photos:
            IncidentPhoto.objects.create(
                incident=self.object,
                photo=photo,
                photo_type='INCIDENT_SCENE',
                uploaded_by=self.request.user
            )
        
        # ===== ADD NOTIFICATION HERE - AFTER INCIDENT IS SAVED =====
        print("\n\n" + "#" * 70)
        print("VIEW: INCIDENT SAVED SUCCESSFULLY")
        print("#" * 70)
        print(f"Report Number: {self.object.report_number}")
        print(f"Incident ID: {self.object.id}")
        print(f"Plant: {self.object.plant}")
        print(f"Location: {self.object.location}")
        print("#" * 70)
        print("\nVIEW: Calling notify_incident_reported()...")

        try:
            from .notifications import notify_incident_reported
            notify_incident_reported(self.object)
            print("\nVIEW: ✅ notify_incident_reported() completed")
        except Exception as e:
            print(f"\nVIEW: ❌ ERROR in notify_incident_reported(): {e}")
            import traceback
            traceback.print_exc()
    
        print("\n" + "#" * 70 + "\n\n")            
        messages.success(
            self.request,
            f'Incident {self.object.report_number} reported successfully! Investigation required within 7 days.'
        )
        
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        print("Form errors:", form.errors)
        print("POST Data - Sublocation:", self.request.POST.get('sublocation'))
        print("POST Data - Location:", self.request.POST.get('location'))
        
        return super().form_invalid(form)

class IncidentDetailView(LoginRequiredMixin, DetailView):
    """View incident details"""
    model = Incident
    template_name = 'accidents/incident_detail.html'
    context_object_name = 'incident'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['photos'] = self.object.photos.all()
        context['action_items'] = self.object.action_items.all()
        
        try:
            context['investigation_report'] = self.object.investigation_report
        except:
            context['investigation_report'] = None
        
        return context


# ============================================================================
# REPLACE YOUR EXISTING IncidentUpdateView WITH THIS UPDATED VERSION
# ============================================================================

class IncidentUpdateView(LoginRequiredMixin, UpdateView):
    """Update incident report"""
    model = Incident
    form_class = IncidentReportForm
    template_name = 'accidents/incident_update.html'
    
    def get_success_url(self):
        return reverse_lazy('accidents:incident_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add departments
        from apps.organizations.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
        # Add employees for affected person dropdown - FIXED QUERY
        context['employees'] = User.objects.filter(
            is_active=True
        ).select_related('department').order_by('first_name', 'last_name')
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        
        if self.request.POST:
            # Update zone queryset
            plant_id = self.request.POST.get('plant')
            if plant_id:
                form.fields['zone'].queryset = Zone.objects.filter(plant_id=plant_id, is_active=True)
            
            # Update location queryset
            zone_id = self.request.POST.get('zone')
            if zone_id:
                form.fields['location'].queryset = Location.objects.filter(zone_id=zone_id, is_active=True)
            
            # Update sublocation queryset
            location_id = self.request.POST.get('location')
            if location_id:
                form.fields['sublocation'].queryset = SubLocation.objects.filter(
                    location_id=location_id,
                    is_active=True
                )
        
        return form
    
    def form_valid(self, form):
        # Handle affected person selection
        affected_person_id = self.request.POST.get('affected_person_id', '').strip()
        if affected_person_id:
            try:
                affected_employee = User.objects.select_related('department').get(
                    id=affected_person_id,
                    is_active=True
                )
                form.instance.affected_person = affected_employee
                form.instance.affected_person_name = affected_employee.get_full_name()
                form.instance.affected_person_employee_id = affected_employee.employee_id or ''
                form.instance.affected_person_department = affected_employee.department
            except (User.DoesNotExist, ValueError):
                pass
        
        # Handle affected body parts JSON
        affected_body_parts_json = self.request.POST.get('affected_body_parts_json', '[]')
        try:
            form.instance.affected_body_parts = json.loads(affected_body_parts_json)
        except:
            form.instance.affected_body_parts = []
        
        # Handle unsafe acts JSON
        unsafe_acts_json = self.request.POST.get('unsafe_acts_json', '[]')
        try:
            form.instance.unsafe_acts = json.loads(unsafe_acts_json)
        except:
            form.instance.unsafe_acts = []
        
        # Handle unsafe acts other explanation
        form.instance.unsafe_acts_other = self.request.POST.get('unsafe_acts_other', '').strip()
        
        # Handle unsafe conditions JSON
        unsafe_conditions_json = self.request.POST.get('unsafe_conditions_json', '[]')
        try:
            form.instance.unsafe_conditions = json.loads(unsafe_conditions_json)
        except:
            form.instance.unsafe_conditions = []
        
        # Handle unsafe conditions other explanation
        form.instance.unsafe_conditions_other = self.request.POST.get('unsafe_conditions_other', '').strip()
        
        # Handle photo uploads
        photos = self.request.FILES.getlist('photos')
        for photo in photos:
            IncidentPhoto.objects.create(
                incident=self.object,
                photo=photo,
                photo_type='INCIDENT_SCENE',
                uploaded_by=self.request.user
            )
        
        messages.success(self.request, f'Incident {self.object.report_number} updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        print("Form errors:", form.errors)
        return super().form_invalid(form)

import json
from django.forms import inlineformset_factory
class InvestigationReportCreateView(LoginRequiredMixin, CreateView):
    """Create investigation report and its associated action items"""
    model = IncidentInvestigationReport
    form_class = IncidentInvestigationReportForm
    template_name = 'accidents/investigation_report_create.html'

    def dispatch(self, request, *args, **kwargs):
        """Ensure the incident exists before proceeding."""
        self.incident = get_object_or_404(Incident, pk=self.kwargs['incident_pk'])
        return super().dispatch(request, *args, **kwargs)

    # ===== NEW/MODIFIED SECTION START =====
    def get_context_data(self, **kwargs):
        """Add the incident and action item formset to the context."""
        context = super().get_context_data(**kwargs)
        context['incident'] = self.incident
        
        # Define the formset for creating action items linked to an incident
        ActionItemFormSet = inlineformset_factory(
            Incident, 
            IncidentActionItem, 
            form=IncidentActionItemForm, 
            extra=1,  # Start with one extra form
            can_delete=False
        )
        
        if self.request.POST:
            context['action_item_formset'] = ActionItemFormSet(self.request.POST, prefix='actionitems')
        else:
            context['action_item_formset'] = ActionItemFormSet(prefix='actionitems')
            
        return context

    def form_valid(self, form):
        """Process the main form and the action item formset."""
        context = self.get_context_data()
        action_item_formset = context['action_item_formset']

        if not action_item_formset.is_valid():
            # If the formset is invalid, re-render the form with errors
            return self.form_invalid(form)

        # 1. Save the main investigation report
        investigation = form.save(commit=False)
        investigation.investigator = self.request.user
        investigation.completed_by = self.request.user
        investigation.incident = self.incident
        
        # Handle root cause factors (existing logic)
        personal_factors_json = self.request.POST.get('personal_factors_json', '[]')
        job_factors_json = self.request.POST.get('job_factors_json', '[]')
        try:
            investigation.personal_factors = json.loads(personal_factors_json)
            investigation.job_factors = json.loads(job_factors_json)
        except json.JSONDecodeError:
            investigation.personal_factors = []
            investigation.job_factors = []
        
        investigation.save()

        # 2. Save the action items from the formset
        action_items = action_item_formset.save(commit=False)
        for item in action_items:
            item.incident = self.incident  # Link each action item to the incident
            item.save()
        
        # Update incident status (existing logic)
        self.incident.investigation_completed_date = investigation.investigation_date
        self.incident.status = 'UNDER_INVESTIGATION'
        self.incident.save()
        
        messages.success(
            self.request, 
            f'Investigation report and action items for {self.incident.report_number} submitted successfully!'
        )
        
        return redirect(self.get_success_url())
    # ===== NEW/MODIFIED SECTION END =====
    
    def get_success_url(self):
        """Redirect to the incident detail page on success."""
        return reverse_lazy('accidents:incident_detail', kwargs={'pk': self.incident.pk})


class ActionItemCreateView(LoginRequiredMixin, CreateView):
    """Create action item"""
    model = IncidentActionItem
    form_class = IncidentActionItemForm
    template_name = 'accidents/action_item_create.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.incident = get_object_or_404(Incident, pk=self.kwargs['incident_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incident'] = self.incident
        return context
    
    def form_valid(self, form):
        form.instance.incident = self.incident
        messages.success(self.request, 'Action item created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('accidents:incident_detail', kwargs={'pk': self.incident.pk})


# AJAX Views
class GetZonesForPlantAjaxView(LoginRequiredMixin, TemplateView):
    """AJAX view to get zones for selected plant"""
    
    def get(self, request, *args, **kwargs):
        plant_id = request.GET.get('plant_id')
        zones = Zone.objects.filter(plant_id=plant_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(zones), safe=False)


class GetLocationsForZoneAjaxView(LoginRequiredMixin, TemplateView):
    """AJAX view to get locations for selected zone"""
    
    def get(self, request, *args, **kwargs):
        zone_id = request.GET.get('zone_id')
        locations = Location.objects.filter(zone_id=zone_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(locations), safe=False)
    
class GetSublocationsForLocationAjaxView(LoginRequiredMixin, TemplateView):
    """AJAX view to get sublocations for selected location"""
    
    def get(self, request, *args, **kwargs):
        location_id = request.GET.get('location_id')
        from apps.organizations.models import SubLocation
        sublocations = SubLocation.objects.filter(
            location_id=location_id, 
            is_active=True
        ).values('id', 'name', 'code')
        return JsonResponse(list(sublocations), safe=False)

    
from django.views import View

class IncidentPDFDownloadView(LoginRequiredMixin, View):
    """Generate PDF report for incident"""
    
    def get(self, request, pk):
        incident = get_object_or_404(Incident, pk=pk)
        
        # Check permissions
        if not (request.user.is_superuser or 
                request.user == incident.reported_by or
                request.user.role in ['ADMIN', 'SAFETY_MANAGER', 'PLANT_HEAD']):
            messages.error(request, "You don't have permission to view this report")
            return redirect('accidents:incident_list')
        
        return generate_incident_pdf(incident)  
    




class IncidentAccidentDashboardView(LoginRequiredMixin, TemplateView):
    """Incident Management Dashboard with Analytics and Filters"""
    template_name = 'accidents/accidents_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date() # Use timezone aware date
        user = self.request.user

        # ==================================================
        # GET FILTER PARAMETERS FROM REQUEST
        # ==================================================
        selected_plant = self.request.GET.get('plant', '')
        selected_zone = self.request.GET.get('zone', '')
        selected_location = self.request.GET.get('location', '')
        selected_sublocation = self.request.GET.get('sublocation', '')
        selected_month = self.request.GET.get('month', '')  # Format: YYYY-MM

        # ==================================================
        # BASE QUERYSET - Filter by user role
        # ==================================================
        if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
            incidents = Incident.objects.all()
        elif getattr(user, 'plant', None):
            incidents = Incident.objects.filter(plant=user.plant)
        else:
            incidents = Incident.objects.filter(reported_by=user)

        # ==================================================
        # APPLY FILTERS TO QUERYSET
        # ==================================================
        if selected_plant:
            incidents = incidents.filter(plant_id=selected_plant)
        if selected_zone:
            incidents = incidents.filter(zone_id=selected_zone)
        if selected_location:
            incidents = incidents.filter(location_id=selected_location)
        if selected_sublocation:
            incidents = incidents.filter(sublocation_id=selected_sublocation)
        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
                incidents = incidents.filter(
                    incident_date__year=year,
                    incident_date__month=month
                )
            except ValueError:
                pass  # Invalid format, ignore filter

        # ==================================================
        # POPULATE FILTER DROPDOWNS
        # ==================================================
        if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
            all_plants = Plant.objects.filter(is_active=True).order_by('name')
        elif getattr(user, 'plant', None):
            all_plants = Plant.objects.filter(id=user.plant.id, is_active=True)
        else:
            all_plants = Plant.objects.none()
        
        context['plants'] = all_plants

        if selected_plant:
            context['zones'] = Zone.objects.filter(plant_id=selected_plant, is_active=True).order_by('name')
            if selected_zone:
                context['locations'] = Location.objects.filter(zone_id=selected_zone, is_active=True).order_by('name')
                if selected_location:
                    context['sublocations'] = SubLocation.objects.filter(location_id=selected_location, is_active=True).order_by('name')
                else:
                    context['sublocations'] = SubLocation.objects.filter(location__zone_id=selected_zone, is_active=True).order_by('name')
            else:
                context['locations'] = Location.objects.filter(zone__plant_id=selected_plant, is_active=True).order_by('name')
                context['sublocations'] = SubLocation.objects.filter(location__zone__plant_id=selected_plant, is_active=True).order_by('name')
        else:
            context['zones'] = Zone.objects.filter(plant__in=all_plants, is_active=True).order_by('name')
            context['locations'] = Location.objects.filter(zone__plant__in=all_plants, is_active=True).order_by('name')
            context['sublocations'] = SubLocation.objects.filter(location__zone__plant__in=all_plants, is_active=True).order_by('name')

        month_options = []
        for i in range(12):
            # Correctly calculate previous months
            current_month = today.month - i
            current_year = today.year
            if current_month <= 0:
                current_month += 12
                current_year -= 1
            date = datetime.date(current_year, current_month, 1)
            month_options.append({
                'value': date.strftime('%Y-%m'),
                'label': date.strftime('%B %Y')
            })
        context['month_options'] = month_options

        # ==================================================
        # STORE SELECTED FILTER VALUES AND NAMES
        # ==================================================
        context['selected_plant'] = selected_plant
        context['selected_zone'] = selected_zone
        context['selected_location'] = selected_location
        context['selected_sublocation'] = selected_sublocation
        context['selected_month'] = selected_month

        # Get names for active filter display
        context['selected_plant_name'] = ''
        context['selected_zone_name'] = ''
        context['selected_location_name'] = ''
        context['selected_sublocation_name'] = ''
        context['selected_month_label'] = ''

        if selected_plant:
            try:
                plant = Plant.objects.get(id=selected_plant)
                context['selected_plant_name'] = plant.name
            except:
                pass

        if selected_zone:
            try:
                zone = Zone.objects.get(id=selected_zone)
                context['selected_zone_name'] = zone.name
            except:
                pass

        if selected_location:
            try:
                location = Location.objects.get(id=selected_location)
                context['selected_location_name'] = location.name
            except:
                pass

        if selected_sublocation:
            try:
                sublocation = SubLocation.objects.get(id=selected_sublocation)
                context['selected_sublocation_name'] = sublocation.name
            except:
                pass

        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
                date_obj = datetime.date(year, month, 1)
                context['selected_month_label'] = date_obj.strftime('%B %Y')
            except:
                pass

        # Flag if any filters are active
        context['has_active_filters'] = bool(
            selected_plant or selected_zone or selected_location or 
            selected_sublocation or selected_month
        )

        # ==================================================
        # BASIC STATISTICS (with filters applied)
        # ==================================================
        context['total_incidents'] = incidents.count()
        context['open_incidents'] = incidents.exclude(status='CLOSED').count()

        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
                context['this_month_incidents'] = incidents.filter(
                    incident_date__year=year,
                    incident_date__month=month
                ).count()
                context['current_month_name'] = datetime.date(year, month, 1).strftime('%B')
                context['current_year'] = year
            except:
                context['this_month_incidents'] = incidents.filter(
                    incident_date__month=today.month,
                    incident_date__year=today.year
                ).count()
                context['current_month_name'] = today.strftime('%B')
                context['current_year'] = today.year
        else:
            context['this_month_incidents'] = incidents.filter(
                incident_date__month=today.month,
                incident_date__year=today.year
            ).count()
            context['current_month_name'] = today.strftime('%B')
            context['current_year'] = today.year
        
        context['investigation_pending'] = incidents.filter(
            investigation_required=True,
            investigation_completed_date__isnull=True
        ).count()

        # ==================================================
        # INCIDENT TYPE COUNTS (For Doughnut Chart)
        # ==================================================
        context['lti_count'] = incidents.filter(incident_type='LTI').count()
        context['mtc_count'] = incidents.filter(incident_type='MTC').count()
        context['fa_count'] = incidents.filter(incident_type='FA').count()
        context['hlfi_count'] = incidents.filter(incident_type='HLFI').count()

        # ==================================================
        # RECENT INCIDENTS & OVERDUE INVESTIGATIONS
        # ==================================================
        context['recent_incidents'] = incidents.select_related(
            'plant', 'location', 'reported_by'
        ).order_by('-reported_date')[:10]
        context['overdue_investigations'] = incidents.filter(
            investigation_required=True,
            investigation_completed_date__isnull=True,
            investigation_deadline__lt=today
        )

        # ==================================================
        # MONTHLY TREND (Last 6 months from filtered data)
        # ==================================================
        # ... (monthly trend logic remains the same)
        six_months_ago = today - datetime.timedelta(days=180)

        monthly_incidents = incidents.filter(
            incident_date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('incident_date')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        monthly_labels = [item['month'].strftime('%b %Y') for item in monthly_incidents]
        monthly_data = [item['count'] for item in monthly_incidents]
        
        context['monthly_labels'] = json.dumps(monthly_labels)
        context['monthly_data'] = json.dumps(monthly_data)

        # ==================================================
        # ****FIXED SECTION****: SEVERITY DISTRIBUTION
        # The model does not have 'severity_level', so we use 'incident_type' instead.
        # This data is for the bar chart named 'severityChart' in the template.
        # ==================================================
        type_distribution = incidents.values('incident_type').annotate(
            count=Count('id')
        )
        
        type_choices_dict = dict(Incident.INCIDENT_TYPES)
        type_dict = {label: 0 for code, label in Incident.INCIDENT_TYPES}

        for item in type_distribution:
            display_name = type_choices_dict.get(item['incident_type'])
            if display_name:
                type_dict[display_name] = item['count']

        # We keep the context variable names the same to avoid changing the template's JavaScript
        context['severity_labels'] = json.dumps(list(type_dict.keys()))
        context['severity_data'] = json.dumps(list(type_dict.values()))

        # ==================================================
        # STATUS DISTRIBUTION
        # ==================================================
        # ... (status distribution logic remains the same)
        status_distribution = incidents.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        status_labels = []
        status_data = []

        for item in status_distribution:
            status_labels.append(
                dict(Incident.STATUS_CHOICES).get(item['status'], item['status'])
            )
            status_data.append(item['count'])

        context['status_labels'] = json.dumps(status_labels)
        context['status_data'] = json.dumps(status_data)

        # ==================================================
        # MONTH-OVER-MONTH % CHANGE
        # ==================================================
        # ... (month-over-month logic remains the same)
        last_month_start = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        last_month_count = incidents.filter(
            incident_date__year=last_month_start.year,
            incident_date__month=last_month_start.month
        ).count()

        current_month_count = context.get('this_month_incidents', 0)

        if last_month_count > 0:
            change = (
                (context['this_month_incidents'] - last_month_count)
                / last_month_count
            ) * 100
            change = round(change, 1) 
        else:
            change = 0

        context['total_incidents_change'] = change
        context['total_incidents_change_abs'] = abs(change)


        return context    

######################Closure 

class IncidentClosureCheckView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Pre-closure verification page"""
    template_name = 'accidents/incident_closure_check.html'
    
    def test_func(self):
        """Check if user has permission to close incidents"""
        return (
            self.request.user.is_superuser or
            self.request.user.can_close_incidents or
            self.request.user.role in ['ADMIN', 'SAFETY_MANAGER', 'PLANT_HEAD']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incident = get_object_or_404(Incident, pk=self.kwargs['pk'])
        
        # Check if incident can be closed
        can_close, message = incident.can_be_closed
        
        # Get investigation status (OneToOneField, not ManyToMany)
        try:
            investigation = incident.investigation_report
        except IncidentInvestigationReport.DoesNotExist:
            investigation = None
        
        # Get action items status
        action_items = incident.action_items.all()
        pending_actions = action_items.exclude(status='COMPLETED')
        completed_actions = action_items.filter(status='COMPLETED')
        
        context.update({
            'incident': incident,
            'can_close': can_close,
            'closure_message': message,
            'investigation': investigation,
            'action_items': action_items,
            'pending_actions': pending_actions,
            'completed_actions': completed_actions,
            'total_actions': action_items.count(),
            'completed_count': completed_actions.count(),
        })
        
        return context


class IncidentClosureView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Close an incident"""
    model = Incident
    form_class = IncidentClosureForm
    template_name = 'accidents/incident_closure.html'
    
    def test_func(self):
        """Check if user has permission to close incidents"""
        return (
            self.request.user.is_superuser or
            self.request.user.can_close_incidents or
            self.request.user.role in ['ADMIN', 'SAFETY_MANAGER', 'PLANT_HEAD']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incident = self.object
        
        # Verify closure eligibility
        can_close, message = incident.can_be_closed
        
        context.update({
            'incident': incident,
            'can_close': can_close,
            'closure_message': message,
        })
        
        return context
    
    def form_valid(self, form):
        incident = form.instance
        
        # Verify incident can be closed
        can_close, message = incident.can_be_closed
        
        if not can_close:
            messages.error(self.request, f"Cannot close incident: {message}")
            return redirect('accidents:incident_detail', pk=incident.pk)
        
        # Set closure details
        incident.closure_date = timezone.now()
        incident.closed_by = self.request.user
        incident.status = 'CLOSED'
        
        messages.success(
            self.request,
            f'Incident {incident.report_number} has been successfully closed.'
        )
        
        # TODO: Send email notification to stakeholders
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('accidents:incident_detail', kwargs={'pk': self.object.pk})


class IncidentReopenView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Reopen a closed incident"""
    
    def test_func(self):
        return (
            self.request.user.is_superuser or
            self.request.user.role in ['ADMIN', 'SAFETY_MANAGER']
        )
    
    def post(self, request, pk):
        incident = get_object_or_404(Incident, pk=pk)
        
        if incident.status != 'CLOSED':
            messages.error(request, "Only closed incidents can be reopened")
            return redirect('accidents:incident_detail', pk=pk)
        
        # Reopen incident
        incident.status = 'UNDER_INVESTIGATION'
        incident.closure_date = None
        incident.closed_by = None
        incident.save()
        
        messages.warning(
            request,
            f'Incident {incident.report_number} has been reopened for further investigation.'
        )
        
        return redirect('accidents:incident_detail', pk=pk)    
    
class InvestigationDetailView(LoginRequiredMixin, DetailView):
    """View investigation report details"""
    model = IncidentInvestigationReport
    template_name = 'accidents/investigation_detail.html'
    context_object_name = 'investigation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incident'] = self.object.incident
        return context    
    


##################notification 
class NotificationListView(LoginRequiredMixin, ListView):
    """List user's notifications"""
    model = IncidentNotification
    template_name = 'accidents/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return IncidentNotification.objects.filter(
            recipient=self.request.user
        ).select_related('incident', 'incident__plant', 'incident__location')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = self.get_queryset().filter(is_read=False).count()
        return context


class MarkNotificationReadView(LoginRequiredMixin, View):
    """Mark notification as read"""
    
    def post(self, request, pk):
        notification = get_object_or_404(
            IncidentNotification, 
            pk=pk, 
            recipient=request.user
        )
        notification.mark_as_read()
        return JsonResponse({'status': 'success'})
#########################################33

class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Mark all notifications as read"""
    
    def post(self, request):
        IncidentNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return JsonResponse({'status': 'success'})   




class IncidentFilterMixin:
    """
    A mixin to provide a filtered queryset of incidents based on URL parameters.
    This can be reused by the Dashboard, Export views, etc.
    """
    def get_filtered_queryset(self):
        user = self.request.user
        
        # Get filter parameters from the URL
        selected_plant = self.request.GET.get('plant', '')
        selected_zone = self.request.GET.get('zone', '')
        selected_location = self.request.GET.get('location', '')
        selected_sublocation = self.request.GET.get('sublocation', '')
        selected_month = self.request.GET.get('month', '')
        selected_type = self.request.GET.get('type', '')
        selected_status = self.request.GET.get('status', '')

        # Base queryset based on user's role
        if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
            base_incidents = Incident.objects.select_related(
                'plant', 'zone', 'location', 'sublocation', 'reported_by', 'closed_by'
            ).all()
        elif getattr(user, 'plant', None):
            base_incidents = Incident.objects.filter(plant=user.plant).select_related(
                'plant', 'zone', 'location', 'sublocation', 'reported_by', 'closed_by'
            )
        else:
            base_incidents = Incident.objects.filter(reported_by=user).select_related(
                'plant', 'zone', 'location', 'sublocation', 'reported_by', 'closed_by'
            )

        # Apply filters
        incidents = base_incidents
        if selected_plant:
            incidents = incidents.filter(plant_id=selected_plant)
        if selected_zone:
            incidents = incidents.filter(zone_id=selected_zone)
        if selected_location:
            incidents = incidents.filter(location_id=selected_location)
        if selected_sublocation:
            incidents = incidents.filter(sublocation_id=selected_sublocation)
        if selected_type:
            incidents = incidents.filter(incident_type=selected_type)
        if selected_status == 'open':
            incidents = incidents.exclude(status='CLOSED')
        elif selected_status:
            incidents = incidents.filter(status=selected_status)

        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
                incidents = incidents.filter(incident_date__year=year, incident_date__month=month)
            except (ValueError, TypeError):
                pass
        
        return incidents.order_by('-incident_date', '-incident_time')
    
class ExportIncidentsExcelView(LoginRequiredMixin, IncidentFilterMixin, View):
    """
    Handles the export of filtered incident data to an Excel file.
    """
    def get(self, request, *args, **kwargs):
        # Use the mixin to get the same filtered data as the dashboard
        queryset = self.get_filtered_queryset()
        
        # Create an in-memory Excel workbook
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Incident Report'

        # Define headers
        headers = [
            'Report Number', 'Incident Type', 'Status', 'Incident Date', 'Incident Time',
            'Plant', 'Zone', 'Location', 'Sub-Location', 'Description', 'Affected Person',
            'Nature of Injury', 'Reported By', 'Reported Date', 'Investigation Deadline',
            'Closure Date', 'Closed By'
        ]
        sheet.append(headers)

        # Style the header row
        for cell in sheet[1]:
            cell.font = openpyxl.styles.Font(bold=True)
            cell.fill = openpyxl.styles.PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")

        # Populate the sheet with data from the queryset
        for incident in queryset:
            row = [
                incident.report_number,
                incident.get_incident_type_display(),
                incident.get_status_display(),
                incident.incident_date,
                incident.incident_time,
                incident.plant.name if incident.plant else 'N/A',
                incident.zone.name if incident.zone else 'N/A',
                incident.location.name if incident.location else 'N/A',
                incident.sublocation.name if incident.sublocation else 'N/A',
                incident.description,
                incident.affected_person_name,
                incident.nature_of_injury,
                incident.reported_by.get_full_name() if incident.reported_by else 'N/A',
                incident.reported_date.strftime("%Y-%m-%d %H:%M") if incident.reported_date else None,
                incident.investigation_deadline,
                incident.closure_date.strftime("%Y-%m-%d %H:%M") if incident.closure_date else None,
                incident.closed_by.get_full_name() if incident.closed_by else 'N/A'
            ]
            sheet.append(row)

        # Set up the HTTP response to return the Excel file
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        # Create a filename with the current date
        filename = f"Incident_Report_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Save the workbook to the response
        workbook.save(response)

        return response

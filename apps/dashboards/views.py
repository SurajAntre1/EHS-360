from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from apps.hazards.models import Hazard
from apps.accidents.models import Incident
from apps.ENVdata.models import MonthlyIndicatorData
from django.shortcuts import redirect
from django.contrib import messages
from apps.organizations.models import Plant # Assuming Plant model is here
from apps.inspections.models import InspectionSchedule
import datetime
from django.db.models import Q # Import Q for complex lookups

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/home.html'
    login_url = 'accounts:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        incidents = Incident.objects.select_related('plant','location','reported_by')
        hazards = Hazard.objects.select_related('plant', 'location', 'reported_by')

        # --- CORRECTED: Use 'assigned_plants' which exists on your User model ---
        user_plants = user.assigned_plants.all()

        if user.is_superuser or getattr(user.role, 'name', None) == 'ADMIN':
            pass
        elif getattr(user.role, 'name', None) == 'EMPLOYEE':
            hazards = hazards.filter(reported_by=user)
            incidents = incidents.filter(reported_by=user)
        # --- CORRECTED: Check if user_plants queryset exists ---
        elif user_plants.exists():
            hazards = hazards.filter(plant__in=user_plants)
            incidents = incidents.filter(plant__in=user_plants)
        else:
            # Fallback for users without assigned plants
            hazards = hazards.filter(reported_by=user)
            incidents = incidents.filter(reported_by=user)

        # inspection = InspectionSchedule.objects.select_related('plant', 'assigned_to', 'template')
        # if user.is_superuser or getattr(user.role, 'name', None) == 'ADMIN':
        #     pass
        # elif getattr(user.role, 'name', None) == 'EMPLOYEE':
        #     inspections = inspection.filter(assigned_to=user)
        # # --- CORRECTED: Check if user_plants queryset exists ---
        # elif user_plants.exists():
        #     inspections = inspection.filter(plant__in=user_plants)
        # else:
        #     inspections = inspection.filter(assigned_to=user)

        context['total_hazards'] = hazards.count()
        context['total_incidents'] = incidents.count()
        # context['total_inspections'] = inspection.count()
        context['total_environmental'] = (MonthlyIndicatorData.objects.values("indicator").distinct().count())
        # context['pending_inspections'] = inspection.filter(status__in=['SCHEDULED', 'IN_PROGRESS', 'OVERDUE']).count()
        context['recent_incidents'] = incidents.order_by('-incident_date')[:5]
        context['recent_hazards'] = hazards.order_by('-reported_date')[:5]

        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings View"""
    template_name = 'dashboards/settings.html'
    login_url = 'accounts:login'


class ApprovalDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard showing all pending, approved, and rejected approvals
    for both Hazards and Incidents, based on the user's role and assigned plants.
    """
    template_name = 'dashboards/approval_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        base_hazards = Hazard.objects.select_related('plant', 'location', 'reported_by')
        base_incidents = Incident.objects.select_related('plant', 'location', 'reported_by', 'incident_type')

        # --- CORRECTED: Use 'assigned_plants' which exists on your User model ---
        user_plants = user.assigned_plants.all()

        # Apply plant-level filter if user is not a superuser/admin and is assigned to plants
        # --- CORRECTED: Check if user_plants queryset exists ---
        if not (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'ADMIN')) and user_plants.exists():
            base_hazards = base_hazards.filter(plant__in=user_plants)
            base_incidents = base_incidents.filter(plant__in=user_plants)

        # --- Fetch Data for Each Tab ---
        context['pending_hazards'] = base_hazards.filter(status='PENDING_APPROVAL').order_by('-reported_date')
        context['pending_incidents'] = base_incidents.filter(status='PENDING_APPROVAL').order_by('-incident_date')
        context['approved_hazards'] = base_hazards.filter(approval_status='APPROVED').order_by('-approved_date')[:20]
        context['approved_incidents'] = base_incidents.filter(approval_status='APPROVED').order_by('-approved_date')[:20]
        context['rejected_hazards'] = base_hazards.filter(approval_status='REJECTED').order_by('-updated_at')[:20]
        context['rejected_incidents'] = base_incidents.filter(approval_status='REJECTED').order_by('-updated_at')[:20]

        # --- Top-level Counts for Badges ---
        context['pending_hazards_count'] = context['pending_hazards'].count()
        context['pending_incidents_count'] = context['pending_incidents'].count()
        context['total_pending'] = context['pending_hazards_count'] + context['pending_incidents_count']

        return context


class PendingHazardsListView(LoginRequiredMixin, ListView):
    """Displays a full, paginated list of all pending hazard approvals."""
    model = Hazard
    template_name = 'dashboards/pending_list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Hazard.objects.filter(status='PENDING_APPROVAL').select_related('plant', 'location', 'reported_by').order_by('-reported_date')
        
        # --- CORRECTED: Use 'assigned_plants' which exists on your User model ---
        user_plants = user.assigned_plants.all()

        # --- CORRECTED: Check if user_plants queryset exists ---
        if not (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'ADMIN')) and user_plants.exists():
            qs = qs.filter(plant__in=user_plants)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item_type'] = 'Hazard'
        context['detail_url_name'] = 'hazards:hazard_detail'
        context['approve_url_name'] = 'hazards:hazard_approve'
        return context


class PendingIncidentsListView(LoginRequiredMixin, ListView):
    """Displays a full, paginated list of all pending incident approvals."""
    model = Incident
    template_name = 'dashboards/pending_list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Incident.objects.filter(status='PENDING_APPROVAL').select_related('plant', 'location', 'reported_by').order_by('-incident_date')
        
        # --- CORRECTED: Use 'assigned_plants' which exists on your User model ---
        user_plants = user.assigned_plants.all()

        # --- CORRECTED: Check if user_plants queryset exists ---
        if not (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'ADMIN')) and user_plants.exists():
            qs = qs.filter(plant__in=user_plants)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item_type'] = 'Incident'
        context['detail_url_name'] = 'accidents:incident_detail'
        context['approve_url_name'] = 'accidents:incident_approve'
        return context
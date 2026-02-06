from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.hazards.models import Hazard
from apps.accidents.models import Incident
# from apps.inspections.models import Inspection
from apps.ENVdata.models import MonthlyIndicatorData
from django.shortcuts import redirect
from django.contrib import messages
from apps.organizations.models import *
from apps.hazards.models import Hazard
from apps.accidents.models import Incident 
import datetime


from django.views.generic import ListView



class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/home.html'
    login_url = 'accounts:login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        incidents = Incident.objects.select_related('plant','location','reported_by')
        hazards = Hazard.objects.select_related('plant', 'location', 'reported_by')

        if user.is_superuser or getattr(user.role, 'name', None) == 'ADMIN':
            pass

        elif getattr(user.role, 'name', None) == 'EMPLOYEE':
            hazards = hazards.filter(reported_by=user)
            incidents = incidents.filter(reported_by=user)

        elif user.plant:
            hazards = hazards.filter(plant=user.plant)
            incidents = incidents.filter(plant=user.plant)

        else:
            hazards = hazards.filter(reported_by=user)
            incidents = incidents.filter(reported_by=user)

        context['total_hazards'] = hazards.count()
        context['total_incidents'] = incidents.count()
        context['total_inspections'] = 0
        context['total_environmental'] = (MonthlyIndicatorData.objects.values("indicator").distinct().count())
        context['pending_inspections'] = 0
        context['recent_incidents'] = incidents.order_by()[:5]
        context['recent_hazards'] = hazards.order_by()[:5]

        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings View"""
    template_name = 'dashboards/settings.html'
    login_url = 'accounts:login'




# class ApprovalDashboardView(LoginRequiredMixin, TemplateView):
#     """Dashboard showing all pending approvals for current user"""
#     template_name = 'dashboards/approval_dashboard.html'
    
#     def dispatch(self, request, *args, **kwargs):
#         # Check if user has approval permission
#         if not request.user.can_approve:
#             messages.error(request, "You don't have permission to access approvals.")
#             return redirect('dashboards:home')
#         return super().dispatch(request, *args, **kwargs)
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
        
#         # Initialize counters
#         context['total_pending'] = 0
#         context['pending_hazards'] = []
#         context['pending_incidents'] = []
#         context['hazards_count'] = 0
#         context['incidents_count'] = 0
        
#         # Get pending hazards if user can approve
#         if user.can_approve_hazards or user.is_superuser:
#             hazards = Hazard.objects.filter(
#                 status='PENDING_APPROVAL',
#                 approval_status='PENDING'
#             ).select_related('plant', 'location', 'reported_by').order_by('-reported_date')
            
#             # Filter by plant if user is plant-specific
#             if not user.is_superuser and user.plant:
#                 hazards = hazards.filter(plant=user.plant)
            
#             context['pending_hazards'] = hazards[:10]  # Show latest 10
#             context['hazards_count'] = hazards.count()
#             context['total_pending'] += hazards.count()
        
#         # Get pending incidents if user can approve
#         if user.can_approve_incidents or user.is_superuser:
#             incidents = Incident.objects.filter(
#                 status='PENDING_APPROVAL',
#                 approval_status='PENDING'
#             ).select_related('plant', 'location', 'reported_by').order_by('-incident_date')
            
#             # Filter by plant if user is plant-specific
#             if not user.is_superuser and user.plant:
#                 incidents = incidents.filter(plant=user.plant)
            
#             context['pending_incidents'] = incidents[:10]  # Show latest 10
#             context['incidents_count'] = incidents.count()
#             context['total_pending'] += incidents.count()
        
#         return context    
    

class ApprovalDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard showing all pending, approved, and rejected approvals
    for both Hazards and Incidents, based on the user's role and plant.
    """
    template_name = 'dashboards/approval_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # --- Base QuerySets with Role-Based Filtering ---
        # Start with all objects
        base_hazards = Hazard.objects.select_related('plant', 'location', 'reported_by')
        base_incidents = Incident.objects.select_related('plant', 'location', 'reported_by', 'incident_type')

        # Apply plant-level filter if user is not a superuser/admin and is assigned to a plant
        if not (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'ADMIN')) and user.plant:
            base_hazards = base_hazards.filter(plant=user.plant)
            base_incidents = base_incidents.filter(plant=user.plant)

        # --- Fetch Data for Each Tab ---
        # 1. Pending Approvals
        context['pending_hazards'] = base_hazards.filter(status='PENDING_APPROVAL').order_by('-reported_date')
        context['pending_incidents'] = base_incidents.filter(status='PENDING_APPROVAL').order_by('-incident_date')

        # 2. Approved Items
        context['approved_hazards'] = base_hazards.filter(approval_status='APPROVED').order_by('-approved_date')[:20]
        context['approved_incidents'] = base_incidents.filter(approval_status='APPROVED').order_by('-approved_date')[:20]

        # 3. Rejected Items
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
        if not (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'ADMIN')) and user.plant:
            qs = qs.filter(plant=user.plant)
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
        if not (user.is_superuser or (hasattr(user, 'role') and user.role.name == 'ADMIN')) and user.plant:
            qs = qs.filter(plant=user.plant)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item_type'] = 'Incident'
        context['detail_url_name'] = 'accidents:incident_detail'
        context['approve_url_name'] = 'accidents:incident_approve'
        return context
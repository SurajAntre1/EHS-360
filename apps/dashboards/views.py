from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.hazards.models import Hazard
from apps.accidents.models import Incident
from apps.inspections.models import Inspection
from apps.ENVdata.models import MonthlyIndicatorData
from django.shortcuts import redirect
from django.contrib import messages
from apps.organizations.models import *



class HomeView(LoginRequiredMixin, TemplateView):
    """Main Dashboard View"""
    template_name = 'dashboards/home.html'
    login_url = 'accounts:login'
    def get_context_data(self, **kwargs):
        hazards = Hazard.objects.all()
        incident = Incident.objects.all()
        inspection = Inspection.objects.all()
        context = super().get_context_data(**kwargs)
        # Add your dashboard data here
        context['total_hazards'] = hazards.count()
        context['total_incidents'] = incident.count()
        context['total_environmental'] = MonthlyIndicatorData.objects.values("indicator").distinct().count()
        context['total_inspections'] = inspection.count()
        context['pending_inspections'] = 0
        return context


class SettingsView(LoginRequiredMixin, TemplateView):
    """Settings View"""
    template_name = 'dashboards/settings.html'
    login_url = 'accounts:login'




class ApprovalDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard showing all pending approvals for current user"""
    template_name = 'dashboards/approval_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has approval permission
        if not request.user.can_approve:
            messages.error(request, "You don't have permission to access approvals.")
            return redirect('dashboards:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Initialize counters
        context['total_pending'] = 0
        context['pending_hazards'] = []
        context['pending_incidents'] = []
        context['hazards_count'] = 0
        context['incidents_count'] = 0
        
        # Get pending hazards if user can approve
        if user.can_approve_hazards or user.is_superuser:
            hazards = Hazard.objects.filter(
                status='PENDING_APPROVAL',
                approval_status='PENDING'
            ).select_related('plant', 'location', 'reported_by').order_by('-reported_date')
            
            # Filter by plant if user is plant-specific
            if not user.is_superuser and user.plant:
                hazards = hazards.filter(plant=user.plant)
            
            context['pending_hazards'] = hazards[:10]  # Show latest 10
            context['hazards_count'] = hazards.count()
            context['total_pending'] += hazards.count()
        
        # Get pending incidents if user can approve
        if user.can_approve_incidents or user.is_superuser:
            incidents = Incident.objects.filter(
                status='PENDING_APPROVAL',
                approval_status='PENDING'
            ).select_related('plant', 'location', 'reported_by').order_by('-incident_date')
            
            # Filter by plant if user is plant-specific
            if not user.is_superuser and user.plant:
                incidents = incidents.filter(plant=user.plant)
            
            context['pending_incidents'] = incidents[:10]  # Show latest 10
            context['incidents_count'] = incidents.count()
            context['total_pending'] += incidents.count()
        
        return context    
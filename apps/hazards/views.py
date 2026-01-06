from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from apps.organizations.models import *
from .models import Hazard, HazardPhoto, HazardActionItem
from django.utils.safestring import mark_safe  # ADD THIS IMPORT

from django.contrib.auth import get_user_model
import datetime
import openpyxl
from openpyxl.utils import get_column_letter
from django.http import JsonResponse, HttpResponse
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from .models import Hazard, HazardPhoto, HazardActionItem


User = get_user_model()


class HazardDashboardView(LoginRequiredMixin, TemplateView):
    """Hazard Management Dashboard"""
    template_name = 'hazards/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get hazards based on user role (This part is already correct)
        if self.request.user.is_superuser or self.request.user.role == 'ADMIN': 
            hazards = Hazard.objects.all()
        elif self.request.user.plant: 
            hazards = Hazard.objects.filter(plant=self.request.user.plant)
        else:
            hazards = Hazard.objects.filter(reported_by=self.request.user)
        
        # Statistics (This part is already correct)
        context['total_hazards'] = hazards.count()
        context['open_hazards'] = hazards.exclude(status__in=['RESOLVED', 'CLOSED']).count()
        context['this_month_hazards'] = hazards.filter(
            incident_datetime__month=datetime.date.today().month,
            incident_datetime__year=datetime.date.today().year
        ).count()
        
        # --- THIS IS THE SECTION TO UPDATE ---
        # Match the context variable names to your template (e.g., 'low_risk' instead of 'low_severity')
        context['critical_hazards'] = hazards.filter(severity='critical').count()
        context['low_risk'] = hazards.filter(severity='low').count()          # <-- UPDATED
        context['medium_risk'] = hazards.filter(severity='medium').count()    # <-- UPDATED
        context['high_risk'] = hazards.filter(severity='high').count()        # <-- UPDATED
        

        # Recent hazards (This part is already correct)
        context['recent_hazards'] = hazards.order_by('-incident_datetime')[:10]
        
        return context


class HazardListView(LoginRequiredMixin, ListView):
    """List all hazards with filtering for category"""
    model = Hazard
    template_name = 'hazards/hazard_list.html'
    context_object_name = 'hazards'
    paginate_by = 20

    def get_queryset(self):
        # La lógica base del queryset es correcta
        if self.request.user.is_superuser or self.request.user.role == 'ADMIN':
            queryset = Hazard.objects.all()
        elif self.request.user.plant:
            queryset = Hazard.objects.filter(plant=self.request.user.plant)
        else:
            queryset = Hazard.objects.filter(reported_by=self.request.user)

        queryset = queryset.select_related('plant', 'location', 'reported_by').order_by('-incident_datetime')

        # --- SECCIÓN ACTUALIZADA ---
        # Obtener todos los parámetros de filtro de la URL (solicitud GET)
        search = self.request.GET.get('search', '')
        hazard_type = self.request.GET.get('hazard_type', '')
        risk_level = self.request.GET.get('risk_level', '') # Corresponde a 'severity' en el modelo
        status = self.request.GET.get('status', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        # Aplicar filtro de búsqueda
        if search:
            queryset = queryset.filter(
                Q(report_number__icontains=search) |
                Q(hazard_title__icontains=search) |
                Q(hazard_description__icontains=search)
            )

        # Aplicar filtros de menú desplegable
        if hazard_type:
            queryset = queryset.filter(hazard_type=hazard_type)

        if risk_level:
            queryset = queryset.filter(severity=risk_level) # Filtrar por el campo 'severity'

        if status:
            queryset = queryset.filter(status=status)

        # Aplicar filtros de fecha
        if date_from:
            queryset = queryset.filter(incident_datetime__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(incident_datetime__date__lte=date_to)
    
        # NEW: Category filter from dashboard click
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(hazard_category=category)
        
        return queryset

    def get_context_data(self, **kwargs):
        # --- NUEVA SECCIÓN AÑADIDA ---
        # Este método envía datos adicionales a la plantilla

        # Primero, obtén el contexto base de la implementación padre
        context = super().get_context_data(**kwargs)

        # 1. Agrega las opciones del menú desplegable al contexto
        #    Esto llenará tus menús <select> con datos del modelo Hazard
        context['hazard_types'] = Hazard.HAZARD_TYPE_CHOICES
        context['risk_levels'] = Hazard.SEVERITY_CHOICES
        context['status_choices'] = Hazard.STATUS_CHOICES

        # 2. Mantén los valores de filtro seleccionados en el formulario después del envío
        #    Esto asegura que después de hacer clic en "Filtrar", los menús desplegables
        #    y los campos de texto muestren los filtros que acabas de aplicar.
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_hazard_type'] = self.request.GET.get('hazard_type', '')
        context['selected_risk_level'] = self.request.GET.get('risk_level', '')
        context['selected_status'] = self.request.GET.get('status', '')

        return context

class HazardCreateView(LoginRequiredMixin, CreateView):
    model = Hazard
    template_name = 'hazards/hazard_create.html'
    success_url = reverse_lazy('hazards:hazard_list')
    fields = []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        
        # Add departments for behalf dropdown
        from apps.organizations.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
        # Add employees for behalf dropdown (active employees)
        context['employees'] = User.objects.filter(
            is_active=True,
            is_active_employee=True
        ).select_related('department').order_by('first_name', 'last_name')
        
        # Add sublocations if user has no assigned sublocation
        if self.request.user.location and not self.request.user.sublocation:
            context['sublocations'] = SubLocation.objects.filter(
                location=self.request.user.location,
                is_active=True
            ).order_by('name')
        
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            hazard = Hazard()
            
            # Reporter and location
            hazard.reported_by = request.user
            hazard.plant = request.user.plant
            hazard.zone = request.user.zone
            hazard.location = request.user.location
            
            # Handle sublocation - Priority to user's assigned sublocation
            if request.user.sublocation:
                hazard.sublocation = request.user.sublocation
            else:
                sublocation_id = request.POST.get('sublocation')
                if sublocation_id and sublocation_id.strip():
                    try:
                        hazard.sublocation = SubLocation.objects.get(id=sublocation_id, is_active=True)
                    except (SubLocation.DoesNotExist, ValueError):
                        hazard.sublocation = None
            
            # Reporter information (only name, email and phone from user model)
            hazard.reporter_name = request.POST.get('reporter_name', '').strip()
            hazard.reporter_email = request.user.email
            hazard.reporter_phone = request.user.phone if hasattr(request.user, 'phone') else ''
            
            # Behalf of information (optional) - Store ForeignKey relationships
            behalf_person_id = request.POST.get('behalf_person_id', '').strip()
            if behalf_person_id:
                try:
                    behalf_employee = User.objects.select_related('department').get(
                        id=behalf_person_id, 
                        is_active=True
                    )
                    hazard.behalf_person = behalf_employee  # Store the User object
                    
                    # Get department from selected dropdown (in case user changed it)
                    behalf_dept_id = request.POST.get('behalf_person_dept', '').strip()
                    if behalf_dept_id:
                        try:
                            from apps.organizations.models import Department
                            dept = Department.objects.get(id=behalf_dept_id, is_active=True)
                            hazard.behalf_person_dept = dept  # Store the Department object
                        except (Department.DoesNotExist, ValueError):
                            # Fallback to employee's department
                            hazard.behalf_person_dept = behalf_employee.department
                    else:
                        # Use employee's department if no department selected
                        hazard.behalf_person_dept = behalf_employee.department
                        
                except (User.DoesNotExist, ValueError):
                    hazard.behalf_person = None
                    hazard.behalf_person_dept = None
            else:
                hazard.behalf_person = None
                hazard.behalf_person_dept = None
            
            # Hazard details
            hazard.hazard_type = request.POST.get('hazard_type')
            hazard.hazard_category = request.POST.get('hazard_category')
            hazard.severity = request.POST.get('severity')
            
            # Auto-generate title from category and type
            hazard.hazard_title = f"{hazard.get_hazard_type_display()} - {hazard.get_hazard_category_display()}"
            hazard.hazard_description = request.POST.get('hazard_description', '').strip()
            
            # Parse datetime
            incident_datetime_str = request.POST.get('incident_datetime')
            if incident_datetime_str:
                hazard.incident_datetime = timezone.datetime.fromisoformat(incident_datetime_str)
            else:
                hazard.incident_datetime = timezone.now()
            
            # Location details
            hazard.location_details = request.POST.get('location_details', '').strip()
            
            # Additional info
            # hazard.immediate_action = request.POST.get('immediate_action', '').strip()
            
            # System fields
            hazard.report_timestamp = request.POST.get('report_timestamp', timezone.now().isoformat())
            hazard.user_agent = request.POST.get('user_agent', '')[:500]
            hazard.report_source = 'web_portal'
            
            # Auto-generate report number
            today = timezone.now().date()
            plant_code = hazard.plant.code if hazard.plant else 'UNKN'
            date_str = today.strftime('%Y%m%d')
            today_count = Hazard.objects.filter(created_at__date=today).count() + 1
            hazard.report_number = f"HAZ-{plant_code}-{date_str}-{today_count:03d}"
            
            # Calculate deadline
            severity_days = {'low': 30, 'medium': 15, 'high': 7, 'critical': 1}
            days = severity_days.get(hazard.severity, 15)
            hazard.action_deadline = today + timezone.timedelta(days=days)
            
            # Set status
            hazard.status = 'REPORTED'
            hazard.approval_status = 'PENDING'
            
            # Save hazard
            hazard.save()
            
            # Handle dynamic photos
            photo_count = int(request.POST.get('photo_count', 1))
            photos_uploaded = 0
            
            for i in range(photo_count):
                photo_file = request.FILES.get(f'photo_{i}')
                if photo_file:
                    HazardPhoto.objects.create(
                        hazard=hazard,
                        photo=photo_file,
                        photo_type='evidence',
                        description=f'Photo {photos_uploaded + 1}',
                        uploaded_by=request.user
                    )
                    photos_uploaded += 1
            
            # Build location info
            location_parts = [hazard.plant.name]
            if hazard.zone:
                location_parts.append(hazard.zone.name)
            location_parts.append(hazard.location.name)
            if hazard.sublocation:
                location_parts.append(hazard.sublocation.name)
            location_info = ' → '.join(location_parts)
            
            # Create formatted success message
            msg_parts = [
                f'✅ <strong>Hazard Report Submitted Successfully!</strong>',
                f'<div class="mt-2">',
                f'<strong>Report Number:</strong> {hazard.report_number}',
                f'<br><strong>Type:</strong> {hazard.get_hazard_type_display()}',
                f'<br><strong>Severity:</strong> {hazard.get_severity_display()}',
                f'<br><strong>Location:</strong> {location_info}',
                f'<br><strong>Action Deadline:</strong> {hazard.action_deadline.strftime("%d %B %Y")}',
            ]
            
            if photos_uploaded > 0:
                msg_parts.append(f'<br><strong>Photos Uploaded:</strong> {photos_uploaded}')
            
            if hazard.behalf_person:
                behalf_dept_name = hazard.behalf_person_dept.name if hazard.behalf_person_dept else 'N/A'
                msg_parts.append(f'<br><strong>Reported on behalf of:</strong> {hazard.behalf_person.get_full_name()} ({behalf_dept_name})')
            
            msg_parts.append('</div>')
            
            success_message = mark_safe(''.join(msg_parts))
            messages.success(request, success_message)
            return redirect(self.success_url)
            
        except Exception as e:
            import traceback
            print("ERROR:", traceback.format_exc())
            messages.error(request, f'Error creating hazard: {str(e)}')
            return redirect('hazards:hazard_create')

class HazardDetailView(LoginRequiredMixin, DetailView):
    """
    Display details of a specific hazard, optimized for performance.
    """
    model = Hazard
    template_name = 'hazards/hazard_detail.html'
    context_object_name = 'hazard'

    def get_queryset(self):
        """
        Optimize the query by pre-fetching related objects to avoid
        multiple database hits in the template.
        """
       
        return Hazard.objects.select_related(
            'plant', 'zone', 'location', 'sublocation',
            'reported_by', 'assigned_to', 'approved_by',
            'behalf_person', 
            'behalf_person_dept'
        ).prefetch_related(
            'photos', 
            'action_items__responsible_person' 
        )

    def get_context_data(self, **kwargs):
        """
        Add the prefetched photos and action items to the context so the
        template can access them directly.
        """
        
        context = super().get_context_data(**kwargs)
        
     
        hazard = self.get_object()
        context['action_items'] = hazard.action_items.all()
        context['photos'] = hazard.photos.all()
        
        return context

class HazardUpdateView(LoginRequiredMixin, UpdateView):
    model = Hazard
    template_name = 'hazards/hazard_update.html'
    fields = []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add departments for behalf dropdown
        from apps.organizations.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
        # Add employees for behalf dropdown (active employees)
        context['employees'] = User.objects.filter(
            is_active=True,
            is_active_employee=True
        ).select_related('department').order_by('first_name', 'last_name')
        
        return context
    
    def get_success_url(self):
        return reverse_lazy('hazards:hazard_detail', kwargs={'pk': self.object.pk})
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        try:
            # Update hazard fields
            self.object.reporter_name = request.POST.get('reporter_name', '').strip()
            self.object.reporter_email = request.POST.get('reporter_email', '').strip()
            self.object.reporter_phone = request.POST.get('reporter_phone', '').strip()
            
            # Behalf of information (optional) - Store ForeignKey relationships
            behalf_person_id = request.POST.get('behalf_person_id', '').strip()
            if behalf_person_id:
                try:
                    behalf_employee = User.objects.select_related('department').get(
                        id=behalf_person_id, 
                        is_active=True
                    )
                    self.object.behalf_person = behalf_employee
                    
                    # Get department from selected dropdown
                    behalf_dept_id = request.POST.get('behalf_person_dept', '').strip()
                    if behalf_dept_id:
                        try:
                            from apps.organizations.models import Department
                            dept = Department.objects.get(id=behalf_dept_id, is_active=True)
                            self.object.behalf_person_dept = dept
                        except (Department.DoesNotExist, ValueError):
                            self.object.behalf_person_dept = behalf_employee.department
                    else:
                        self.object.behalf_person_dept = behalf_employee.department
                        
                except (User.DoesNotExist, ValueError):
                    self.object.behalf_person = None
                    self.object.behalf_person_dept = None
            else:
                self.object.behalf_person = None
                self.object.behalf_person_dept = None
            
            self.object.hazard_type = request.POST.get('hazard_type')
            self.object.hazard_category = request.POST.get('hazard_category')
            self.object.severity = request.POST.get('severity')
            self.object.hazard_title = request.POST.get('hazard_title', '').strip()
            self.object.hazard_description = request.POST.get('hazard_description', '').strip()
            
            # Parse datetime
            incident_datetime_str = request.POST.get('incident_datetime')
            if incident_datetime_str:
                self.object.incident_datetime = timezone.datetime.fromisoformat(incident_datetime_str)
            
            # Location details
            self.object.location_details = request.POST.get('location_details', '').strip()
            
            # GPS
            gps_lat = request.POST.get('gps_latitude', '').strip()
            gps_long = request.POST.get('gps_longitude', '').strip()
            self.object.gps_latitude = gps_lat if gps_lat else None
            self.object.gps_longitude = gps_long if gps_long else None
            
            # Additional info
            self.object.injury_status = request.POST.get('injury_status', '')
            # self.object.immediate_action = request.POST.get('immediate_action', '').strip()
            self.object.witnesses = request.POST.get('witnesses', '').strip()
            
            # Recalculate deadline if severity changed
            severity_days = {'low': 30, 'medium': 15, 'high': 7, 'critical': 1}
            days = severity_days.get(self.object.severity, 15)
            # Keep original reported date for deadline calculation
            base_date = self.object.reported_date.date()
            self.object.action_deadline = base_date + timezone.timedelta(days=days)
            
            # Save the hazard
            self.object.save()
            
            # Handle photo deletions
            for key in request.POST:
                if key.startswith('keep_photo_') and request.POST[key] == '0':
                    photo_id = key.replace('keep_photo_', '')
                    try:
                        photo = HazardPhoto.objects.get(id=photo_id, hazard=self.object)
                        photo.delete()
                    except HazardPhoto.DoesNotExist:
                        pass
            
            # Handle new photos
            photos_uploaded = 0
            for i in range(5):
                photo_file = request.FILES.get(f'photo_{i}')
                if photo_file:
                    HazardPhoto.objects.create(
                        hazard=self.object,
                        photo=photo_file,
                        photo_type='evidence',
                        description=f'Additional Photo {i+1}',
                        uploaded_by=request.user
                    )
                    photos_uploaded += 1
            
            # Build behalf info for success message
            behalf_info = ''
            if self.object.behalf_person:
                behalf_dept_name = self.object.behalf_person_dept.name if self.object.behalf_person_dept else 'N/A'
                behalf_info = f'<br><strong>On Behalf Of:</strong> {self.object.behalf_person.get_full_name()} ({behalf_dept_name})'
            
            # Success message
            msg = f'''
            <div class="alert-content">
                <i class="fas fa-check-circle text-success"></i> 
                <strong>Hazard Report Updated Successfully!</strong>
                <div class="mt-2">
                    <strong>Report Number:</strong> {self.object.report_number}<br>
                    <strong>Updated Deadline:</strong> {self.object.action_deadline.strftime("%d %B %Y")}
                    {f'<br><strong>New Photos Added:</strong> {photos_uploaded}' if photos_uploaded > 0 else ''}
                    {behalf_info}
                </div>
            </div>
            '''
            
            messages.success(request, mark_safe(msg))
            return redirect(self.get_success_url())
            
        except Exception as e:
            import traceback
            print("ERROR:", traceback.format_exc())
            messages.error(request, f'Error updating hazard: {str(e)}')
            return redirect('hazards:hazard_update', pk=self.object.pk)


class HazardActionItemCreateView(LoginRequiredMixin, CreateView):
    """Create action item for hazard"""
    model = HazardActionItem
    template_name = 'hazards/action_item_create.html'
    fields = ['action_description', 'responsible_person', 'target_date', 'status']
    
    def dispatch(self, request, *args, **kwargs):
        self.hazard = get_object_or_404(Hazard, pk=self.kwargs['hazard_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hazard'] = self.hazard
        context['users'] = User.objects.filter(is_active=True)
        if self.hazard.action_deadline:
            context['action_deadline_date'] = self.hazard.action_deadline.strftime('%Y-%m-%d')
        return context
    
    def form_valid(self, form):
        form.instance.hazard = self.hazard
        messages.success(self.request, 'Action item created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('hazards:hazard_detail', kwargs={'pk': self.hazard.pk})
    def post(self, request, *args, **kwargs):
        try:
            action_item = HazardActionItem()
            
            action_item.hazard = self.hazard
            action_item.action_description = request.POST.get('action_description', '').strip()
            
            # Responsible Person
            responsible_person_id = request.POST.get('responsible_person')
            if responsible_person_id:
                action_item.responsible_person = User.objects.get(id=responsible_person_id)
            
            # Target Date - PARSE THE STRING TO DATE
            target_date_str = request.POST.get('target_date')
            if target_date_str:
                from datetime import datetime
                action_item.target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            
            # Force status to PENDING on creation
            action_item.status = 'PENDING'
            
            action_item.save()
            
            messages.success(request, 'Action item created successfully with Pending status!')
            return redirect(self.get_success_url())
            
        except Exception as e:
            import traceback
            print("ERROR:", traceback.format_exc())
            messages.error(request, f'Error creating action item: {str(e)}')
            return redirect('hazards:action_item_create', hazard_pk=self.hazard.pk)
class HazardActionItemUpdateView(LoginRequiredMixin, UpdateView):
    """Update action item"""
    model = HazardActionItem
    template_name = 'hazards/action_item_update.html'
    fields = ['action_description', 'responsible_person', 'target_date', 'status', 'completion_date', 'completion_remarks']
    
    def get_success_url(self):
        return reverse_lazy('hazards:hazard_detail', kwargs={'pk': self.object.hazard.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Action item updated successfully!')
        return super().form_valid(form)
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        try:
            # Update fields
            self.object.action_description = request.POST.get('action_description', '').strip()
            
            responsible_person_id = request.POST.get('responsible_person')
            if responsible_person_id:
                self.object.responsible_person = User.objects.get(id=responsible_person_id)
            
            # Target Date - PARSE THE STRING TO DATE
            target_date_str = request.POST.get('target_date')
            if target_date_str:
                from datetime import datetime
                self.object.target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            
            # Update status
            self.object.status = request.POST.get('status', 'PENDING')
            
            # If completed, save completion details
            if self.object.status == 'COMPLETED':
                completion_date_str = request.POST.get('completion_date')
                if completion_date_str:
                    from datetime import datetime

                    self.object.completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d').date()
                
                self.object.completion_remarks = request.POST.get('completion_remarks', '').strip()
            
            self.object.save()
            
            messages.success(request, f'Action item updated successfully! Status: {self.object.get_status_display()}')
            return redirect(self.get_success_url())
            
        except Exception as e:
            import traceback
            print("ERROR:", traceback.format_exc())
            messages.error(request, f'Error updating action item: {str(e)}')
            return redirect('hazards:action_item_update', pk=self.object.pk)

# AJAX Views for cascading dropdowns
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
    
    
    
    
import datetime
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Count
from django.db.models.functions import TruncMonth

# Make sure all models are imported
from .models import Hazard
from apps.organizations.models import Plant, Zone, Location, SubLocation

from .models import Hazard
from apps.organizations.models import Plant, Zone, Location, SubLocation


class HazardDashboardViews(LoginRequiredMixin, TemplateView):
    """
    Advanced Hazard Management Dashboard with working filters.
    """
    template_name = 'hazards/hazards_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = datetime.date.today()

        # 1. URL se saare filter parameters get karo
        selected_plant = self.request.GET.get('plant', '')
        selected_zone = self.request.GET.get('zone', '')
        selected_location = self.request.GET.get('location', '')
        selected_sublocation = self.request.GET.get('sublocation', '')
        selected_month = self.request.GET.get('month', '')
        selected_severity = self.request.GET.get('severity', '')
        selected_status = self.request.GET.get('status', '')

        # 2. User ke role ke hisaab se base query banao
        if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
            base_hazards = Hazard.objects.all()
            all_plants = Plant.objects.filter(is_active=True).order_by('name')
        elif getattr(user, 'plant', None):
            base_hazards = Hazard.objects.filter(plant=user.plant)
            all_plants = Plant.objects.filter(id=user.plant.id)
        else:
            base_hazards = Hazard.objects.filter(reported_by=user)
            all_plants = Plant.objects.none()

        # 3. Base query par filters apply karo
        hazards = base_hazards
        if selected_plant:
            hazards = hazards.filter(plant_id=selected_plant)
        if selected_zone:
            hazards = hazards.filter(zone_id=selected_zone)
        if selected_location:
            hazards = hazards.filter(location_id=selected_location)
        if selected_sublocation:
            hazards = hazards.filter(sublocation_id=selected_sublocation)
        if selected_severity:
            hazards = hazards.filter(severity=selected_severity)
        if selected_status == 'open':
             hazards = hazards.exclude(status__in=['RESOLVED', 'CLOSED'])
        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
                hazards = hazards.filter(incident_datetime__year=year, incident_datetime__month=month)
            except (ValueError, TypeError):
                pass
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if date_from:
            hazards = hazards.filter(incident_datetime__date__gte=date_from)

        if date_to:
            hazards = hazards.filter(incident_datetime__date__lte=date_to)

        # 4. Dropdown options ko populate karo (filtered)
        context['plants'] = all_plants
        
        zone_qs = Zone.objects.filter(is_active=True)
        if selected_plant:
            zone_qs = zone_qs.filter(plant_id=selected_plant)
        context['zones'] = zone_qs.order_by('name')

        location_qs = Location.objects.filter(is_active=True)
        if selected_zone:
            location_qs = location_qs.filter(zone_id=selected_zone)
        elif selected_plant and not selected_zone: # Agar sirf plant selected hai
             location_qs = location_qs.filter(zone__plant_id=selected_plant)
        context['locations'] = location_qs.order_by('name')

        sublocation_qs = SubLocation.objects.filter(is_active=True)
        if selected_location:
            sublocation_qs = sublocation_qs.filter(location_id=selected_location)
        elif selected_zone and not selected_location: # Agar sirf zone selected hai
             sublocation_qs = sublocation_qs.filter(location__zone_id=selected_zone)
        context['sublocations'] = sublocation_qs.order_by('name')
        
        context['month_options'] = [{
            'value': (today - datetime.timedelta(days=i*30)).strftime('%Y-%m'),
            'label': (today - datetime.timedelta(days=i*30)).strftime('%B %Y')
        } for i in range(12)]

        # 5. Selected values ko template mein wapas bhejo
        context.update({
            'selected_plant': selected_plant, 'selected_zone': selected_zone,
            'selected_location': selected_location, 'selected_sublocation': selected_sublocation,
            'selected_month': selected_month, 'selected_severity': selected_severity,
            'selected_status': selected_status,
            'date_from': date_from,
            'date_to': date_to,         #for filter with date 
        })
        try:
            if selected_plant: context['selected_plant_name'] = Plant.objects.get(id=selected_plant).name
            if selected_zone: context['selected_zone_name'] = Zone.objects.get(id=selected_zone).name
            if selected_location: context['selected_location_name'] = Location.objects.get(id=selected_location).name
            if selected_sublocation: context['selected_sublocation_name'] = SubLocation.objects.get(id=selected_sublocation).name
            if selected_month:
                year, month = map(int, selected_month.split('-'))
                context['selected_month_label'] = datetime.date(year, month, 1).strftime('%B %Y')
        except:
             pass
        context['has_active_filters'] = any(context.get(key) for key in ['selected_plant', 'selected_zone', 'selected_location', 'selected_sublocation', 'selected_month', 'selected_severity', 'selected_status'])

        # 6. Statistics calculate karo (filtered data par)
        context['total_hazards'] = hazards.count()
        context['open_hazards'] = hazards.exclude(status__in=['RESOLVED', 'CLOSED']).count()
        context['this_month_hazards'] = hazards.count() if selected_month else hazards.filter(incident_datetime__year=today.year, incident_datetime__month=today.month).count()
        context['overdue_hazards_count'] = hazards.filter(action_deadline__lt=today).exclude(status__in=['RESOLVED', 'CLOSED']).count()
        context['recent_hazards'] = hazards.select_related('plant', 'location').order_by('-incident_datetime')[:10]

        # 7. NEW: Top 3 Hazard Categories
        top_categories_query = hazards.values('hazard_category').annotate(count=Count('hazard_category')).order_by('-count')[:3]
        category_display_map = dict(Hazard.HAZARD_CATEGORIES)
        top_categories_list = []
        for item in top_categories_query:
            top_categories_list.append({
                'value': item['hazard_category'],
                'display_name': category_display_map.get(item['hazard_category'], 'Unknown'),
                'count': item['count']
            })
        context['top_hazard_categories'] = top_categories_list

        # 8. Prepare Chart Data (on filtered data)
        # Monthly Trend
        six_months_ago = today - datetime.timedelta(days=180)
        monthly_hazards = hazards.filter(incident_datetime__gte=six_months_ago).annotate(month=TruncMonth('incident_datetime')).values('month').annotate(count=Count('id')).order_by('month')
        context['monthly_labels'] = json.dumps([item['month'].strftime('%b %Y') for item in monthly_hazards])
        context['monthly_data'] = json.dumps([item['count'] for item in monthly_hazards])

        # Severity Distribution
        severity_distribution = hazards.values('severity').annotate(count=Count('id'))
        severity_dict = {item['severity']: item['count'] for item in severity_distribution}
        severity_labels = [choice[1] for choice in Hazard.SEVERITY_CHOICES]
        severity_values = [choice[0] for choice in Hazard.SEVERITY_CHOICES]
        context['severity_labels'] = json.dumps(severity_labels)
        context['severity_data'] = json.dumps([severity_dict.get(val, 0) for val in severity_values])

        # Status Distribution
        status_distribution = hazards.values('status').annotate(count=Count('id')).order_by('-count')
        status_labels = [dict(Hazard.STATUS_CHOICES).get(item['status'], item['status']) for item in status_distribution]
        status_data = [item['count'] for item in status_distribution]
        context['status_labels'] = json.dumps(status_labels)
        context['status_data'] = json.dumps(status_data)


        return context
    

# ==================================================
# AJAX VIEWS for Cascading Dropdowns
# These views must exist to support the dashboard filters.
# ==================================================

class GetZonesForPlantAjaxView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        plant_id = request.GET.get('plant_id')
        if not plant_id: return JsonResponse([], safe=False)
        zones = Zone.objects.filter(plant_id=plant_id, is_active=True).values('id', 'name')
        return JsonResponse(list(zones), safe=False)

class GetLocationsForZoneAjaxView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        zone_id = request.GET.get('zone_id')
        if not zone_id: return JsonResponse([], safe=False)
        locations = Location.objects.filter(zone_id=zone_id, is_active=True).values('id', 'name')
        return JsonResponse(list(locations), safe=False)

# This view was missing from your urls.py but is needed for the functionality
class GetSubLocationsForLocationAjaxView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        location_id = request.GET.get('location_id')
        if not location_id: return JsonResponse([], safe=False)
        sublocations = SubLocation.objects.filter(location_id=location_id, is_active=True).values('id', 'name')
        return JsonResponse(list(sublocations), safe=False)

# NOTE: Your other views like HazardListView, HazardCreateView, etc. can remain as they are.

class GetSubLocationsForLocationAjaxView(LoginRequiredMixin, TemplateView):
    """
    AJAX view to get sublocations for a selected location.
    This is called by the JavaScript on the dashboard page.
    """
    def get(self, request, *args, **kwargs):
        # Get the 'location_id' from the GET parameters of the request.
        location_id = request.GET.get('location_id')
        
        # If no location_id is provided, return an empty JSON array.
        if not location_id: 
            return JsonResponse([], safe=False)
            
        # Filter SubLocation objects that are active and belong to the selected location.
        # .values('id', 'name') ensures we only fetch the data we need.
        sublocations = SubLocation.objects.filter(location_id=location_id, is_active=True).values('id', 'name')
        
        # Return the queryset as a JSON response.
        return JsonResponse(list(sublocations), safe=False)
class ExportHazardsView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):

        user = self.request.user
        if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
            hazards = Hazard.objects.all()
        elif getattr(user, 'plant', None):
            hazards = Hazard.objects.filter(plant=user.plant)
        else:
            hazards = Hazard.objects.filter(reported_by=user)

        filter_params = {
            'plant': request.GET.get('plant'),
            'zone': request.GET.get('zone'),
            'location': request.GET.get('location'),
            'sublocation': request.GET.get('sublocation'),
            'severity': request.GET.get('severity'),
            'status': request.GET.get('status'),
            'month': request.GET.get('month'),
        }

        if filter_params['plant']:
            hazards = hazards.filter(plant_id=filter_params['plant'])
        if filter_params['zone']:
            hazards = hazards.filter(zone_id=filter_params['zone'])
        if filter_params['location']:
            hazards = hazards.filter(location_id=filter_params['location'])
        if filter_params['sublocation']:
            hazards = hazards.filter(sublocation_id=filter_params['sublocation'])
        if filter_params['severity']:
            hazards = hazards.filter(severity=filter_params['severity'])
        if filter_params['status'] == 'open':
            hazards = hazards.exclude(status__in=['RESOLVED', 'CLOSED'])
        if filter_params['month']:
            try:
                year, month = map(int, filter_params['month'].split('-'))
                hazards = hazards.filter(incident_datetime__year=year, incident_datetime__month=month)
            except (ValueError, TypeError):
                pass


        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Hazards Report'


        title_font = Font(name='Calibri', size=18, bold=True, color='002060')
        header_font = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid')
        header_align = Alignment(horizontal='center', vertical='center')
        cell_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                             top=Side(style='thin'), bottom=Side(style='thin'))


        critical_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid') # Red
        high_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')     # Yellow
        resolved_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid') # Green


        sheet.merge_cells('A1:O1')
        title_cell = sheet['A1']
        title_cell.value = 'Hazards Export Report'
        title_cell.font = title_font
        title_cell.alignment = Alignment(horizontal='center')

        sheet.append([f"Report Generated On: {datetime.date.today().strftime('%d %B %Y')}"])
        sheet.append([])


        headers = [
            'Report Number', 'Title', 'Type', 'Category', 'Severity', 'Status',
            'Incident Datetime', 'Reported By', 'Reported Date', 'Plant', 'Zone',
            'Location', 'Sub-Location', 'Description', 'Action Deadline'
        ]
        sheet.append(headers)
        header_row = sheet.max_row

        for cell in sheet[header_row]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border


        for hazard in hazards.select_related('plant', 'zone', 'location', 'sublocation', 'reported_by'):
            row_data = [
                hazard.report_number,
                hazard.hazard_title,
                hazard.get_hazard_type_display(),
                hazard.get_hazard_category_display(),
                hazard.get_severity_display(),
                hazard.get_status_display(),
                hazard.incident_datetime.strftime('%Y-%m-%d %H:%M') if hazard.incident_datetime else '',
                hazard.reported_by.get_full_name() if hazard.reported_by else 'N/A',
                hazard.created_at.strftime('%Y-%m-%d') if hazard.created_at else '',
                hazard.plant.name if hazard.plant else 'N/A',
                hazard.zone.name if hazard.zone else 'N/A',
                hazard.location.name if hazard.location else 'N/A',
                hazard.sublocation.name if hazard.sublocation else 'N/A',
                hazard.hazard_description,
                hazard.action_deadline.strftime('%Y-%m-%d') if hazard.action_deadline else ''
            ]
            sheet.append(row_data)
            current_row = sheet.max_row
            
            for cell in sheet[current_row]:
                cell.alignment = cell_align
                cell.border = thin_border

          
            severity_cell = sheet[f'E{current_row}']
            if hazard.severity == 'critical':
                severity_cell.fill = critical_fill
            elif hazard.severity == 'high':
                severity_cell.fill = high_fill

            status_cell = sheet[f'F{current_row}']
            if hazard.status in ['RESOLVED', 'CLOSED']:
                status_cell.fill = resolved_fill

       
        for col_idx, column_cells in enumerate(sheet.columns, 1):
            max_length = 0
            column_letter = get_column_letter(col_idx)
            for cell in column_cells:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
          
            adjusted_width = (max_length + 2)
            if adjusted_width < 15:
                adjusted_width = 15
            if adjusted_width > 50:
                adjusted_width = 50 
            sheet.column_dimensions[column_letter].width = adjusted_width

   
        sheet.freeze_panes = 'A5' 


        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="hazards_report_{datetime.date.today()}.xlsx"'

        workbook.save(response)
        return response
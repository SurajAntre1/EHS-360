from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from apps.accounts.views import AdminRequiredMixin
from django.http import JsonResponse
from django.views import View
from .models import *
from .forms import *
from django.forms import ValidationError


class OrganizationDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Organization Setup Dashboard"""
    template_name = 'organizations/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Plants
        context['total_plants'] = Plant.objects.count()
        context['active_plants'] = Plant.objects.filter(is_active=True).count()
        
        # Zones
        context['total_zones'] = Zone.objects.count()
        context['active_zones'] = Zone.objects.filter(is_active=True).count()
        
        # Locations
        context['total_locations'] = Location.objects.count()
        context['active_locations'] = Location.objects.filter(is_active=True).count()
        
        # Sub-Locations
        context['total_sublocations'] = SubLocation.objects.count()
        context['active_sublocations'] = SubLocation.objects.filter(is_active=True).count()
        
        # Departments
        context['total_departments'] = Department.objects.count()
        context['active_departments'] = Department.objects.filter(is_active=True).count()
        
        # Employees (from User model)
        from apps.accounts.models import User
        context['total_employees'] = User.objects.filter(is_superuser=False).count()
        context['active_employees'] = User.objects.filter(is_superuser=False, is_active=True).count()
        
        return context

# ==================== PLANT VIEWS ====================

class PlantListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all plants"""
    model = Plant
    template_name = 'organizations/plant_list.html'
    context_object_name = 'plants'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Plant.objects.annotate(
            zones_count=Count('zones', distinct=True),
            locations_count=Count('zones__locations', distinct=True),
            sublocations_count=Count('zones__locations__sublocations', distinct=True)
        )
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(city__icontains=search) |
                Q(state__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class PlantCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new plant"""
    model = Plant
    form_class = PlantForm
    template_name = 'organizations/plant_form.html'
    success_url = reverse_lazy('organizations:plant_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Plant {form.instance.name} created successfully!')
        return super().form_valid(form)


class PlantUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update plant"""
    model = Plant
    form_class = PlantForm
    template_name = 'organizations/plant_form.html'
    success_url = reverse_lazy('organizations:plant_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Plant {form.instance.name} updated successfully!')
        return super().form_valid(form)


class PlantDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete plant"""
    model = Plant
    template_name = 'organizations/plant_confirm_delete.html'
    success_url = reverse_lazy('organizations:plant_list')
    
    def delete(self, request, *args, **kwargs):
        plant = self.get_object()
        messages.success(request, f'Plant {plant.name} deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ==================== LOCATION VIEWS ====================
from django.http import JsonResponse
from django.views import View

class GetZonesForPlantView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """AJAX view to get zones for a selected plant"""
    
    def get(self, request, *args, **kwargs):
        plant_id = request.GET.get('plant_id')
        zones = Zone.objects.filter(plant_id=plant_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(zones), safe=False)
    
class GetLocationsForZoneAjaxView(LoginRequiredMixin, View):
    """AJAX view to get locations for selected zone"""
    
    def get(self, request):
        zone_id = request.GET.get('zone_id')
        locations = Location.objects.filter(zone_id=zone_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(locations), safe=False)


class GetSubLocationsAjaxView(LoginRequiredMixin, View):
    """AJAX view to get sublocations for selected location"""
    
    def get(self, request):
        location_id = request.GET.get('location_id')
        sublocations = SubLocation.objects.filter(
            location_id=location_id, 
            is_active=True
        ).values('id', 'name', 'code')
        return JsonResponse(list(sublocations), safe=False)    
# Update the LocationListView get_queryset method
class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = 'organizations/location_list.html'
    context_object_name = 'locations'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Location.objects.select_related('zone', 'zone__plant').prefetch_related('sublocations')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(zone__name__icontains=search) |
                Q(zone__plant__name__icontains=search)
            )
        
        # Filter by plant
        plant_id = self.request.GET.get('plant')
        if plant_id:
            queryset = queryset.filter(zone__plant_id=plant_id)
        
        # Filter by zone
        zone_id = self.request.GET.get('zone')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('zone__plant__name', 'zone__name', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plants'] = Plant.objects.filter(is_active=True)
        context['zones'] = Zone.objects.filter(is_active=True).select_related('plant')
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_plant'] = self.request.GET.get('plant', '')
        context['selected_zone'] = self.request.GET.get('zone', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context

class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = 'organizations/location_form.html'
    success_url = reverse_lazy('organizations:location_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plants'] = Plant.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        # Don't save plant field as it's not in the model
        response = super().form_valid(form)
        
        # Process sublocations
        sublocation_count = int(self.request.POST.get('sublocation_count', 0))
        
        for i in range(sublocation_count):
            name = self.request.POST.get(f'sublocation_name_{i}', '').strip()
            code = self.request.POST.get(f'sublocation_code_{i}', '').strip()
            description = self.request.POST.get(f'sublocation_description_{i}', '').strip()
            is_active = self.request.POST.get(f'sublocation_active_{i}') == '1'
            
            if name:  # Only create if name is provided
                SubLocation.objects.create(
                    location=self.object,
                    name=name,
                    code=code.upper() if code else '',
                    description=description,
                    is_active=is_active
                )
        
        messages.success(self.request, f'Location "{self.object.name}" created successfully with {sublocation_count} sub-locations!')
        return response



class LocationUpdateView(LoginRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = 'organizations/location_form.html'
    success_url = reverse_lazy('organizations:location_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plants'] = Plant.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Track existing sublocation IDs
        existing_sublocation_ids = []
        
        # Process sublocations
        sublocation_count = int(self.request.POST.get('sublocation_count', 0))
        
        for i in range(sublocation_count):
            sublocation_id = self.request.POST.get(f'sublocation_id_{i}')
            name = self.request.POST.get(f'sublocation_name_{i}', '').strip()
            code = self.request.POST.get(f'sublocation_code_{i}', '').strip()
            description = self.request.POST.get(f'sublocation_description_{i}', '').strip()
            is_active = self.request.POST.get(f'sublocation_active_{i}') == '1'
            
            if name:
                if sublocation_id:
                    # Update existing sublocation
                    try:
                        sublocation = SubLocation.objects.get(id=sublocation_id, location=self.object)
                        sublocation.name = name
                        sublocation.code = code.upper() if code else ''
                        sublocation.description = description
                        sublocation.is_active = is_active
                        sublocation.save()
                        existing_sublocation_ids.append(int(sublocation_id))
                    except SubLocation.DoesNotExist:
                        pass
                else:
                    # Create new sublocation
                    new_sublocation = SubLocation.objects.create(
                        location=self.object,
                        name=name,
                        code=code.upper() if code else '',
                        description=description,
                        is_active=is_active
                    )
                    existing_sublocation_ids.append(new_sublocation.id)
        
        # Delete sublocations that were removed
        SubLocation.objects.filter(location=self.object).exclude(id__in=existing_sublocation_ids).delete()
        
        messages.success(self.request, f'Location "{self.object.name}" updated successfully!')
        return response

class LocationDeleteView(LoginRequiredMixin, DeleteView):
    model = Location
    success_url = reverse_lazy('organizations:location_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Location deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ==================== DEPARTMENT VIEWS ====================
from django.shortcuts import redirect

class DepartmentListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all departments"""
    model = Department
    template_name = 'organizations/department_list.html'
    context_object_name = 'departments'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Department.objects.all().annotate(
            total_employees=Count('users'),
            active_employees=Count('users', filter=Q(users__is_active=True))
        ).order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class DepartmentCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new department"""
    model = Department
    form_class = DepartmentForm
    template_name = 'organizations/department_form.html'
    success_url = reverse_lazy('organizations:department_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Department {form.instance.name} created successfully!')
        return super().form_valid(form)


class DepartmentUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update department"""
    model = Department
    form_class = DepartmentForm
    template_name = 'organizations/department_form.html'
    success_url = reverse_lazy('organizations:department_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Department {form.instance.name} updated successfully!')
        return super().form_valid(form)


class DepartmentDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete department"""
    model = Department
    template_name = 'organizations/department_confirm_delete.html'
    success_url = reverse_lazy('organizations:department_list')
    
    def delete(self, request, *args, **kwargs):
        department = self.get_object()
        messages.success(request, f'Department {department.name} deleted successfully!')
        return super().delete(request, *args, **kwargs)
    




# ==================== ZONE VIEWS ====================

class ZoneListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all zones"""
    model = Zone
    template_name = 'organizations/zone_list.html'
    context_object_name = 'zones'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Zone.objects.select_related('plant').prefetch_related(
            'locations',
            'locations__sublocations'
        ).annotate(
            total_locations=Count('locations', distinct=True),
            active_locations=Count('locations', filter=Q(locations__is_active=True), distinct=True)
        ).order_by('-created_at')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(plant__name__icontains=search)
            )
        
        # Filter by plant
        plant = self.request.GET.get('plant')
        if plant:
            queryset = queryset.filter(plant_id=plant)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plants'] = Plant.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_plant'] = self.request.GET.get('plant', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context



class ZoneCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new zone with locations and sublocations"""
    model = Zone
    form_class = ZoneForm
    template_name = 'organizations/zone_form.html'
    success_url = reverse_lazy('organizations:zone_list')
    
    def form_valid(self, form):
        # Save the zone first
        self.object = form.save()
        
        # DEBUG: Print all POST data
        print("=" * 50)
        print("POST DATA:")
        for key, value in self.request.POST.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        # Process locations
        location_count = int(self.request.POST.get('location_count', 0))
        print(f"Location count: {location_count}")
        
        for i in range(location_count):
            location_name = self.request.POST.get(f'location_name_{i}', '').strip()
            location_code = self.request.POST.get(f'location_code_{i}', '').strip()
            location_description = self.request.POST.get(f'location_description_{i}', '').strip()
            location_active = self.request.POST.get(f'location_active_{i}') == '1'
            
            print(f"\nProcessing Location {i}:")
            print(f"  Name: {location_name}")
            print(f"  Code: {location_code}")
            print(f"  Active: {location_active}")
            
            if location_name and location_code:
                # Create location 
                loc_data = {
                    'plant': self.object.plant.id,
                    'zone': self.object.id,
                    'name': location_name,
                    'code': location_code.upper(),
                    'description': location_description,
                    'is_active': location_active,
                }
                
                # Use LocationForm for validation
                loc_form = LocationForm(loc_data)
                if loc_form.is_valid():
                    new_location = loc_form.save()
                    print(f"  ✓ Location created via form: {new_location.id}")
                else:
                    print(f"  ✗ Location skipped due to validation error: {loc_form.errors}")
                    messages.error(self.request, f"Location '{location_name}': {loc_form.errors.as_text()}")

                # Process sublocations for this location
                sublocation_count_input = self.request.POST.get(f'sublocation_count_{i}', 0)
                try:
                    sublocation_count = int(sublocation_count_input)
                except:
                    sublocation_count = 0
                
                print(f"  Sublocation count: {sublocation_count}")
                
                for j in range(sublocation_count):
                    subloc_name = self.request.POST.get(f'location_{i}_sublocation_name_{j}', '').strip()
                    subloc_code = self.request.POST.get(f'location_{i}_sublocation_code_{j}', '').strip()
                    subloc_active = self.request.POST.get(f'location_{i}_sublocation_active_{j}') == '1'
                    
                    # print(f"    Sublocation {j}:")
                    # print(f"      Name: {subloc_name}")
                    # print(f"      Code: {subloc_code}")
                    # print(f"      Active: {subloc_active}")
                    
                    if subloc_name:
                        new_subloc = SubLocation.objects.create(
                            location=new_location,
                            name=subloc_name,
                            code=subloc_code.upper() if subloc_code else '',
                            is_active=subloc_active
                        )
                        print(f"      ✓ Sublocation created: {new_subloc.id}")
                    else:
                        print(f"      ✗ Sublocation skipped (no name)")
            else:
                print(f"  ✗ Location skipped (missing name or code)")
        
        messages.success(
            self.request, 
            f'Zone "{self.object.name}" created successfully with {location_count} location(s)!'
        )
        return redirect(self.success_url)


class ZoneUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update zone with locations and sublocations"""
    model = Zone
    form_class = ZoneForm
    template_name = 'organizations/zone_form.html'
    success_url = reverse_lazy('organizations:zone_list')
    
    def form_valid(self, form):
        self.object = form.save()
        
        # DEBUG: Print all POST data
        print("=" * 50)
        print("UPDATE - POST DATA:")
        for key, value in self.request.POST.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        # Track existing location IDs
        existing_location_ids = []
        
        # Process locations
        location_count = int(self.request.POST.get('location_count', 0))
        print(f"Location count: {location_count}")
        
        for i in range(location_count):
            location_id = self.request.POST.get(f'location_id_{i}')
            location_name = self.request.POST.get(f'location_name_{i}', '').strip()
            location_code = self.request.POST.get(f'location_code_{i}', '').strip()
            location_description = self.request.POST.get(f'location_description_{i}', '').strip()
            location_active = self.request.POST.get(f'location_active_{i}') == '1'
            
            # print(f"\nProcessing Location {i}:")
            # print(f"  ID: {location_id}")
            # print(f"  Name: {location_name}")
            # print(f"  Code: {location_code}")
            # print(f"  Active: {location_active}")

            if location_name and location_code:
                loc_data = {
                    'plant': self.object.plant.id,
                    'zone': self.object.id,
                    'name': location_name,
                    'code': location_code.upper(),
                    'description': location_description,
                    'is_active': location_active,
                }

                if location_id:
                    # Update existing location
                    try:
                        location_instance = Location.objects.get(id=location_id, zone=self.object)
                        loc_form = LocationForm(loc_data, instance=location_instance)
                        if loc_form.is_valid():
                            location = loc_form.save()
                            existing_location_ids.append(location.id)
                            print(f"  ✓ Location updated via form: {location.id}")
                        else:
                            print(f"  ✗ Location validation failed: {loc_form.errors}")
                            messages.error(self.request, f"Location '{location_name}': {loc_form.errors.as_text()}")
                            continue
                    except Location.DoesNotExist:
                        print(f"  ✗ Location not found: {location_id}")
                        continue
                else:
                    # Create new location via form
                    loc_form = LocationForm(loc_data)
                    if loc_form.is_valid():
                        location = loc_form.save()
                        existing_location_ids.append(location.id)
                        print(f"  ✓ New location created via form: {location.id}")
                    else:
                        print(f"  ✗ Location validation failed: {loc_form.errors}")
                        messages.error(self.request, f"Location '{location_name}': {loc_form.errors.as_text()}")
                        continue

                # Process sublocations
                existing_sublocation_ids = []
                sublocation_count_input = self.request.POST.get(f'sublocation_count_{i}', 0)
                try:
                    sublocation_count = int(sublocation_count_input)
                except:
                    sublocation_count = 0

                print(f"  Sublocation count: {sublocation_count}")

                for j in range(sublocation_count):
                    subloc_id = self.request.POST.get(f'location_{i}_sublocation_id_{j}')
                    subloc_name = self.request.POST.get(f'location_{i}_sublocation_name_{j}', '').strip()
                    subloc_code = self.request.POST.get(f'location_{i}_sublocation_code_{j}', '').strip()
                    subloc_active = self.request.POST.get(f'location_{i}_sublocation_active_{j}') == '1'

                    # print(f"    Sublocation {j}:")
                    # print(f"      ID: {subloc_id}")
                    # print(f"      Name: {subloc_name}")

                    if subloc_name:
                        if subloc_id:
                            # Update existing sublocation
                            try:
                                subloc = SubLocation.objects.get(id=subloc_id, location=location)
                                subloc.name = subloc_name
                                subloc.code = subloc_code.upper() if subloc_code else ''
                                subloc.is_active = subloc_active
                                subloc.save()
                                existing_sublocation_ids.append(subloc.id)
                                print(f"      ✓ Sublocation updated: {subloc.id}")
                            except SubLocation.DoesNotExist:
                                print(f"      ✗ Sublocation not found: {subloc_id}")
                        else:
                            # Create new sublocation
                            new_subloc = SubLocation.objects.create(
                                location=location,
                                name=subloc_name,
                                code=subloc_code.upper() if subloc_code else '',
                                is_active=subloc_active
                            )
                            existing_sublocation_ids.append(new_subloc.id)
                            print(f"      ✓ Sublocation created: {new_subloc.id}")

                # Delete removed sublocations
                deleted_sublocs = SubLocation.objects.filter(location=location).exclude(
                    id__in=existing_sublocation_ids
                )
                print(f"  Deleting {deleted_sublocs.count()} sublocations")
                deleted_sublocs.delete()

        deleted_locs = Location.objects.filter(zone=self.object).exclude(id__in=existing_location_ids)
        print(f"Deleting {deleted_locs.count()} locations")
        deleted_locs.delete()
        
        messages.success(self.request, f'Zone "{self.object.name}" updated successfully!')
        return redirect(self.success_url)

class ZoneDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete zone"""
    model = Zone
    template_name = 'organizations/zone_confirm_delete.html'
    success_url = reverse_lazy('organizations:zone_list')
    
    def delete(self, request, *args, **kwargs):
        zone = self.get_object()
        messages.success(request, f'Zone {zone.name} deleted successfully!')
        return super().delete(request, *args, **kwargs)    
    


class GetAllPlantsAjaxView(LoginRequiredMixin, View):
    """Get all active plants"""
    def get(self, request):
        plants = Plant.objects.filter(is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(plants), safe=False)



class GetZonesByPlantsAjaxView(LoginRequiredMixin, View):
    """Get zones filtered by multiple plant IDs"""
    def get(self, request):
        plant_ids = request.GET.get('plant_ids', '').split(',')
        plant_ids = [pid for pid in plant_ids if pid]
        
        if plant_ids:
            zones = Zone.objects.filter(
                plant_id__in=plant_ids,
                is_active=True
            ).select_related('plant').order_by('plant__name', 'name')
            
            result = []
            for zone in zones:
                result.append({
                    'id': zone.id,
                    'name': zone.name,
                    'code': zone.code,
                    'plant_name': zone.plant.name
                })
            return JsonResponse(result, safe=False)
        return JsonResponse([], safe=False)


class GetLocationsByZonesAjaxView(LoginRequiredMixin, View):
    """Get locations filtered by multiple zone IDs"""
    def get(self, request):
        zone_ids = request.GET.get('zone_ids', '').split(',')
        zone_ids = [zid for zid in zone_ids if zid]
        
        if zone_ids:
            locations = Location.objects.filter(
                zone_id__in=zone_ids,
                is_active=True
            ).select_related('zone').order_by('zone__name', 'name')
            
            result = []
            for location in locations:
                result.append({
                    'id': location.id,
                    'name': location.name,
                    'code': location.code,
                    'zone_name': location.zone.name
                })
            return JsonResponse(result, safe=False)
        return JsonResponse([], safe=False)


class GetSublocationsByLocationsAjaxView(LoginRequiredMixin, View):
    """Get sublocations filtered by multiple location IDs"""
    def get(self, request):
        location_ids = request.GET.get('location_ids', '').split(',')
        location_ids = [lid for lid in location_ids if lid]
        
        if location_ids:
            sublocations = SubLocation.objects.filter(
                location_id__in=location_ids,
                is_active=True
            ).select_related('location').order_by('location__name', 'name')
            
            result = []
            for sublocation in sublocations:
                result.append({
                    'id': sublocation.id,
                    'name': sublocation.name,
                    'code': sublocation.code or '',
                    'location_name': sublocation.location.name
                })
            return JsonResponse(result, safe=False)
        return JsonResponse([], safe=False)
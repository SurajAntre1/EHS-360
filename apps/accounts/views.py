from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from django.db.models import Q
from .models import User,Role,Permissions
from .forms import UserCreationFormCustom, UserUpdateForm
from apps.organizations.models import *
from apps.accidents.utils import get_incidents_for_user


class CustomLoginView(LoginView):
    """Custom Login View for EHS-360"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        user = self.request.user
        
        # If superuser (created via createsuperuser), redirect to Django admin
        if user.is_superuser:
            return '/admin/'
        
        # Otherwise redirect to dashboard
        return reverse_lazy('dashboards:home')
    
    def form_valid(self, form):
        user = form.get_user()
        
        # Check if superuser
        if user.is_superuser:
            messages.success(
                self.request, 
                f'Welcome, {user.get_full_name() or user.username}! Redirecting to Admin Panel...'
            )
        else:
            messages.success(
                self.request, 
                f'Welcome back, {user.get_full_name() or user.username}!'
            )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(
            self.request, 
            'Invalid username or password. Please try again.'
        )
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Custom Logout View"""
    next_page = 'accounts:login'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You have been successfully logged out.')
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require admin access"""
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.is_superuser or
            (user.role and user.role.name == 'ADMIN')
        )
    
    def handle_no_permission(self):
        messages.error(self.request, 'You do not have permission to access this page.')
        return redirect('dashboards:home')


class ProfileView(LoginRequiredMixin, TemplateView):
    """User Profile View"""
    template_name = 'accounts/profile.html'
    login_url = 'accounts:login'
    
    def dispatch(self, request, *args, **kwargs):
        # Block superuser from accessing profile
        if request.user.is_superuser:
            messages.warning(request, 'Superadmin cannot access this page.')
            return redirect('/admin/')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """List all users - Only accessible by Admin"""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        # Exclude superuser accounts - they are NOT employees
        queryset = User.objects.filter(is_superuser=False).order_by('-date_joined')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(employee_id__icontains=search)
            )
        
        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role__name=role)
        
        # Filter by active status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Count only employees (exclude superuser)
        context['total_users'] = User.objects.filter(is_superuser=False).count()
        context['active_users'] = User.objects.filter(is_superuser=False, is_active=True).count()
        context['inactive_users'] = User.objects.filter(is_superuser=False, is_active=False).count()
        context['role_choices'] = User.ROLE_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_role'] = self.request.GET.get('role', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new user"""
    model = User
    form_class = UserCreationFormCustom
    template_name = 'accounts/user_create.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def form_valid(self, form):
        # Save user first
        user = form.save(commit=False)
        user.save()
        
        # Handle MULTIPLE PLANT ASSIGNMENTS (from checkboxes)
        assigned_plants = self.request.POST.getlist('assigned_plants')
        if assigned_plants:
            user.assigned_plants.set(assigned_plants)
            # Set first plant as primary
            user.plant = Plant.objects.get(id=assigned_plants[0])
        
        # Handle MULTIPLE ZONE ASSIGNMENTS (from checkboxes)
        assigned_zones = self.request.POST.getlist('assigned_zones')
        if assigned_zones:
            user.assigned_zones.set(assigned_zones)
            # Set first zone as primary
            user.zone = Zone.objects.get(id=assigned_zones[0])
        
        # Save user with primary plant/zone
        user.save()
        
        # Handle MULTIPLE LOCATION ASSIGNMENTS (from checkboxes)
        assigned_locations = self.request.POST.getlist('assigned_locations')
        if assigned_locations:
            user.assigned_locations.set(assigned_locations)
            # Set first location as primary
            user.location = Location.objects.get(id=assigned_locations[0])
            user.save()
        
        # Handle MULTIPLE SUBLOCATION ASSIGNMENTS (from checkboxes)
        assigned_sublocations = self.request.POST.getlist('assigned_sublocations')
        if assigned_sublocations:
            user.assigned_sublocations.set(assigned_sublocations)
            # Set first sublocation as primary
            user.sublocation = SubLocation.objects.get(id=assigned_sublocations[0])
            user.save()
        
        # Success message
        plant_count = user.assigned_plants.count()
        zone_count = user.assigned_zones.count()
        loc_count = user.assigned_locations.count()
        subloc_count = user.assigned_sublocations.count()
        
        messages.success(
            self.request, 
            f'User "{user.get_full_name()}" created successfully! '
            f'Assigned: {plant_count} plant(s), {zone_count} zone(s), '
            f'{loc_count} location(s), {subloc_count} sub-location(s).'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Update user - Only accessible by Admin"""
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_update.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Load all active plants
        context['all_plants'] = Plant.objects.filter(is_active=True).order_by('name')
        
        # Get user's existing assignments as Python lists
        user = self.object
        context['user_assigned_plants'] = list(user.assigned_plants.all().values_list('id', flat=True))
        context['user_assigned_zones'] = list(user.assigned_zones.all().values_list('id', flat=True))
        context['user_assigned_locations'] = list(user.assigned_locations.all().values_list('id', flat=True))
        context['user_assigned_sublocations'] = list(user.assigned_sublocations.all().values_list('id', flat=True))
        
        return context
    
    def form_valid(self, form):
        # Save user first
        user = form.save(commit=False)
        user.save()
        
        # Handle MULTIPLE PLANT ASSIGNMENTS (from checkboxes)
        assigned_plants = self.request.POST.getlist('assigned_plants')
        if assigned_plants:
            user.assigned_plants.set(assigned_plants)
            # Set first plant as primary
            user.plant = Plant.objects.get(id=assigned_plants[0])
        else:
            user.assigned_plants.clear()
            user.plant = None
        
        # Handle MULTIPLE ZONE ASSIGNMENTS (from checkboxes)
        assigned_zones = self.request.POST.getlist('assigned_zones')
        if assigned_zones:
            user.assigned_zones.set(assigned_zones)
            # Set first zone as primary
            user.zone = Zone.objects.get(id=assigned_zones[0])
        else:
            user.assigned_zones.clear()
            user.zone = None
        
        # Save user with primary plant/zone
        user.save()
        
        # Handle MULTIPLE LOCATION ASSIGNMENTS (from checkboxes)
        assigned_locations = self.request.POST.getlist('assigned_locations')
        if assigned_locations:
            user.assigned_locations.set(assigned_locations)
            # Set first location as primary
            user.location = Location.objects.get(id=assigned_locations[0])
            user.save()
        else:
            user.assigned_locations.clear()
            user.location = None
            user.save()
        
        # Handle MULTIPLE SUBLOCATION ASSIGNMENTS (from checkboxes)
        assigned_sublocations = self.request.POST.getlist('assigned_sublocations')
        if assigned_sublocations:
            user.assigned_sublocations.set(assigned_sublocations)
            # Set first sublocation as primary
            user.sublocation = SubLocation.objects.get(id=assigned_sublocations[0])
            user.save()
        else:
            user.assigned_sublocations.clear()
            user.sublocation = None
            user.save()
        
        messages.success(
            self.request, 
            f'User {user.username} updated successfully!'
        )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        print("Form errors:", form.errors)
        return super().form_invalid(form)
    
    def get_queryset(self):
        queryset = get_incidents_for_user(self.request.user)
        queryset = queryset.select_related('plant','zone','location','reported_by')
        return User.objects.filter(is_superuser=False)

class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete user - Only accessible by Admin"""
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def get_queryset(self):
        # Prevent deleting superuser accounts
        return User.objects.filter(is_superuser=False)
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        messages.success(request, f'User {user.username} deleted successfully!')
        return super().delete(request, *args, **kwargs)


class UserDetailView(LoginRequiredMixin, TemplateView):
    """View user details - Only accessible by Admin"""
    template_name = 'accounts/user_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('pk')
        # Only show employee details, not superuser
        user_obj = get_object_or_404(
            User.objects.filter(is_superuser=False), 
            pk=user_id
        )
        context['user_detail'] = user_obj
        return context


class UserToggleActiveView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Toggle user active status"""
    
    def post(self, request, pk):
        # Only allow toggling for employees, not superuser
        user = get_object_or_404(
            User.objects.filter(is_superuser=False), 
            pk=pk
        )
        
        user.is_active = not user.is_active
        user.save()
        
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.username} has been {status}.')
        return redirect('accounts:user_list')
    

######## permission module i am creating   ###########################
# class UserPermissionsOnlyView(LoginRequiredMixin, AdminRequiredMixin, ListView):
#     """
#     Separate page ONLY for managing permissions
#     Shows users with checkboxes for module access and approval permissions
#     """
#     model = User
#     template_name = 'accounts/permissions_only.html'
#     context_object_name = 'users'
#     paginate_by = 15
    
#     def get_queryset(self):
#         queryset = User.objects.filter(is_active=True).exclude(
#             is_superuser=True
#         ).select_related('plant', 'department').order_by('first_name', 'last_name')
        
#         # Search filter
#         search = self.request.GET.get('search')
#         if search:
#             queryset = queryset.filter(
#                 Q(first_name__icontains=search) |
#                 Q(last_name__icontains=search) |
#                 Q(username__icontains=search) |
#                 Q(email__icontains=search) |
#                 Q(employee_id__icontains=search)
#             )
        
#         # Role filter
#         role = self.request.GET.get('role')
#         if role:
#             queryset = queryset.filter(role__name=role)
        
#         # Plant filter
#         plant_id = self.request.GET.get('plant')
#         if plant_id:
#             queryset = queryset.filter(plant_id=plant_id)
        
#         return queryset
    
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         from apps.organizations.models import Plant
        
#         context['roles'] = Role.objects.all()
#         context['plants'] = Plant.objects.filter(is_active=True)
#         context['search_query'] = self.request.GET.get('search', '')
        
#         # Statistics
#         context['total_users'] = User.objects.filter(is_active=True).exclude(is_superuser=True).count()
#         context['users_with_incident_access'] = User.objects.filter(can_access_incident_module=True).count()
#         context['users_with_hazard_access'] = User.objects.filter(can_access_hazard_module=True).count()
#         context['hazard_approvers'] = User.objects.filter(can_approve_hazards=True).count()
#         context['incident_approvers'] = User.objects.filter(can_approve_incidents=True).count()
        
#         return context


# def update_user_permission(request, user_id):
#     """
#     AJAX endpoint to update a single permission for a user
#     """
#     if not (request.user.is_superuser or request.user.role.name == 'ADMIN' and request.user.role.name == 'ADMIN'):
#         return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
#     if request.method == 'POST':
#         user = get_object_or_404(User, pk=user_id)
#         permission_field = request.POST.get('permission_field')
#         value = request.POST.get('value') == 'true'
        
#         # List of valid permission fields
#         valid_fields = [
#             'can_access_incident_module',
#             'can_access_hazard_module',
#             'can_access_inspection_module',
#             'can_access_audit_module',
#             'can_access_training_module',
#             'can_access_permit_module',
#             'can_access_observation_module',
#             'can_access_reports_module',
#             'can_approve_incidents',
#             'can_approve_hazards',
#             'can_approve_inspections',
#             'can_approve_permits',
#             'can_close_incidents',
#             'can_close_hazards',
#         ]
        
#         if permission_field in valid_fields:
#             setattr(user, permission_field, value)
#             user.save()
            
#             messages.success(
#                 request, 
#                 f"{'Granted' if value else 'Revoked'} {permission_field.replace('_', ' ').title()} for {user.get_full_name()}"
#             )
            
#             return JsonResponse({
#                 'success': True,
#                 'message': f"Permission updated for {user.get_full_name()}"
#             })
#         else:
#             return JsonResponse({'success': False, 'error': 'Invalid permission field'}, status=400)
    
#     return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


# def bulk_update_permissions(request):
#     """
#     Bulk update permissions for multiple users
#     """
#     if not (request.user.is_superuser or request.user.role.name == 'ADMIN'):
#         messages.error(request, "You don't have permission to perform this action.")
#         return redirect('accounts:permissions_only')
    
#     if request.method == 'POST':
#         user_ids = request.POST.getlist('user_ids')
#         permission_field = request.POST.get('permission_field')
#         action = request.POST.get('action')  # 'grant' or 'revoke'
        
#         if not user_ids:
#             messages.error(request, "No users selected")
#             return redirect('accounts:permissions_only')
        
#         users = User.objects.filter(id__in=user_ids)
        
#         # List of valid permission fields
#         valid_fields = [
#             'can_access_incident_module',
#             'can_access_hazard_module',
#             'can_access_inspection_module',
#             'can_access_audit_module',
#             'can_access_training_module',
#             'can_access_permit_module',
#             'can_access_observation_module',
#             'can_access_reports_module',
#             'can_approve_incidents',
#             'can_approve_hazards',
#             'can_approve_inspections',
#             'can_approve_permits',
#             'can_close_incidents',
#             'can_close_hazards',
#         ]
        
#         if permission_field in valid_fields:
#             value = action == 'grant'
#             users.update(**{permission_field: value})
            
#             perm_name = permission_field.replace('_', ' ').replace('can ', '').title()
#             messages.success(
#                 request, 
#                 f"{action.title()}ed {perm_name} permission for {len(user_ids)} user(s)"
#             )
#         else:
#             messages.error(request, "Invalid permission field")
        
#         return redirect('accounts:permissions_only')
    
#     return redirect('accounts:permissions_only')  



class GetSubLocationsAjaxView(LoginRequiredMixin, View):
    """AJAX view to get sublocations for selected location"""
    
    def get(self, request):
        location_id = request.GET.get('location_id')
        sublocations = SubLocation.objects.filter(
            location_id=location_id, 
            is_active=True
        ).values('id', 'name', 'code')
        return JsonResponse(list(sublocations), safe=False)

# =======================
# Role and permission
#========================
class RolePermission(LoginRequiredMixin, TemplateView):
    template_name = 'roles/role_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.all()
        return context
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search = self.request.GET.get('search', '')
        roles = Role.objects.all()
        if search:
            roles = roles.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        context['roles'] = roles
        context['search_query'] = search
        return context
    
class RoleCreateView(LoginRequiredMixin, TemplateView):
    """Assigning user roles"""
    template_name = 'roles/roles_permission.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['permission'] = Permissions.objects.all()
        return context

    def post(self, request):
        role_name = request.POST.get("role_name", "").strip()
        description = request.POST.get("description", "").strip()

        permission_ids = [
            pid for pid in request.POST.getlist("permissions") if pid
        ]

        if not role_name:
            messages.error(request, "Role name is required")
            return redirect('accounts:createrole')

        if Role.objects.filter(name=role_name).exists():
            messages.error(request, "Role name already exists")
            return redirect('accounts:createrole')

        role = Role.objects.create(
            name=role_name,
            description=description
        )

        if permission_ids:
            permissions = Permissions.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)

        messages.success(request, "Role created successfully")
        return redirect('accounts:role-list')
    
class RoleUpdateView(LoginRequiredMixin, TemplateView):
    """Update an existing role"""
    template_name = 'roles/roleupdate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role_id = self.kwargs.get('role_id')
        role = get_object_or_404(Role, id=role_id)

        context['role'] = role
        context['permission'] = Permissions.objects.all()
        context['role_permissions'] = role.permissions.values_list('id', flat=True)
        return context

    def post(self, request, *args, **kwargs):
        role_id = self.kwargs.get('role_id')
        role = get_object_or_404(Role, id=role_id)

        role_name = request.POST.get("role_name", "").strip()
        description = request.POST.get("description", "").strip()
        permission_ids = [
            pid for pid in request.POST.getlist("permissions") if pid
        ]

        if not role_name:
            messages.error(request, "Role name is required")
            return redirect('accounts:updaterole', role_id=role.id)

        if Role.objects.filter(name=role_name).exclude(id=role.id).exists():
            messages.error(request, "Role name already exists")
            return redirect('accounts:updaterole', role_id=role.id)

        role.name = role_name
        role.description = description
        role.save()
        if permission_ids:
            permissions = Permissions.objects.filter(id__in=permission_ids)
            role.permissions.set(permissions)
        else:
            role.permissions.clear()

        messages.success(request, "Role updated successfully")
        return redirect('accounts:role-list')
    

###########################Role-permissin#############################

class RolePermissionsHierarchicalView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Hierarchical permission management with module grouping"""
    template_name = 'roles/role_permissions_hierarchical.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role_id = self.kwargs.get('role_id')
        role = get_object_or_404(Role, id=role_id)
        
        context['role'] = role
        context['role_permission_ids'] = list(role.permissions.values_list('id', flat=True))
        
        # Group permissions by module
        modules = {}
        module_choices = dict(Permissions._meta.get_field('module').choices)
        
        for module_code, module_name in module_choices.items():
            # Get all permissions for this module
            module_perms = Permissions.objects.filter(
                module=module_code
            ).order_by('display_order')
            
            if module_perms.exists():
                # Separate module access from other permissions
                access_perm = module_perms.filter(permission_type='MODULE_ACCESS').first()
                other_perms = module_perms.exclude(permission_type='MODULE_ACCESS')
                
                # Check if role has access
                has_access = access_perm and (access_perm.id in context['role_permission_ids'])
                
                modules[module_code] = {
                    'name': module_name,
                    'access_permission': access_perm,
                    'has_access': has_access,
                    'permissions': other_perms
                }
        
        context['modules'] = modules
        
        return context


def toggle_module_access(request, role_id):
    """Toggle module access - grants/revokes parent permission"""
    if not (request.user.is_superuser or (request.user.role and request.user.role.name == 'ADMIN')):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        role = get_object_or_404(Role, id=role_id)
        module_code = request.POST.get('module_code')
        action = request.POST.get('action')  # 'grant' or 'revoke'
        
        try:
            # Get module access permission
            access_perm = Permissions.objects.get(
                module=module_code,
                permission_type='MODULE_ACCESS'
            )
            
            if action == 'grant':
                # Grant module access
                role.permissions.add(access_perm)
                message = f"Granted access to {access_perm.name}"
                
            elif action == 'revoke':
                # Revoke module access AND all child permissions
                role.permissions.remove(access_perm)
                
                # Remove ALL permissions in this module
                module_perms = Permissions.objects.filter(module=module_code)
                role.permissions.remove(*module_perms)
                
                message = f"Revoked access to {access_perm.name} and all related permissions"
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
            
            # Count users affected
            user_count = role.role_user.count()
            
            return JsonResponse({
                'success': True,
                'message': message,
                'module_code': module_code,
                'has_access': action == 'grant',
                'affected_users': user_count
            })
            
        except Permissions.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Module access permission not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


def toggle_permission_in_module(request, role_id):
    """Toggle individual permission - only works if module access granted"""
    if not (request.user.is_superuser or (request.user.role and request.user.role.name == 'ADMIN')):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        role = get_object_or_404(Role, id=role_id)
        permission_id = request.POST.get('permission_id')
        action = request.POST.get('action')  # 'add' or 'remove'
        
        try:
            permission = Permissions.objects.get(id=permission_id)
            
            # Check if role has module access
            has_module_access = role.permissions.filter(
                module=permission.module,
                permission_type='MODULE_ACCESS'
            ).exists()
            
            if not has_module_access and action == 'add':
                return JsonResponse({
                    'success': False,
                    'error': f'Must grant "{permission.module}" module access first'
                }, status=400)
            
            if action == 'add':
                role.permissions.add(permission)
                message = f"Added '{permission.name}'"
            elif action == 'remove':
                role.permissions.remove(permission)
                message = f"Removed '{permission.name}'"
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
            
            return JsonResponse({
                'success': True,
                'message': message,
                'permission_count': role.permissions.count()
            })
            
        except Permissions.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Permission not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
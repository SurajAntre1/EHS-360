from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import AccessMixin

class PermissionRequiredMixin(AccessMixin):
    """
    Mixin to check if user has required permission
    Usage: Set 'permission_required' attribute in your view
    """
    permission_required = None
    
    def dispatch(self, request, *args, **kwargs):
        if not self.permission_required:
            raise ValueError("permission_required must be set")
        
        # Check permission
        if not (request.user.has_permission(self.permission_required) or request.user.is_superuser):
            messages.error(request, "You don't have permission to perform this action.")
            return redirect('dashboards:home')
        
        return super().dispatch(request, *args, **kwargs)
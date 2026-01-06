from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class SuperAdminAccessMiddleware:
    """
    Middleware to ensure superuser (created via createsuperuser) can only access Django admin panel
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Allow access to admin panel, static files, and login/logout
        allowed_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/accounts/login/',
            '/accounts/logout/',
        ]
        
        # Check if path starts with any allowed path
        path_allowed = any(request.path.startswith(path) for path in allowed_paths)
        
        # If user is authenticated and is superuser
        if request.user.is_authenticated and request.user.is_superuser:
            # If trying to access web app (not admin panel)
            if not path_allowed:
                messages.warning(
                    request, 
                    'Superadmin can only access Django Admin Panel. Please use /admin/ URL.'
                )
                return redirect('/admin/')
        
        response = self.get_response(request)
        return response
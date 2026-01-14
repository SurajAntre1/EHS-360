from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User,Role,Permissions


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users"""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'employee_id', 'phone')


class CustomUserChangeForm(UserChangeForm):
    """Custom form for changing users"""
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'employee_id', 'is_active', 'is_staff', 'is_superuser']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'employee_id']
    
    fieldsets = UserAdmin.fieldsets + (
        ('EHS-360 Information', {
            'fields': ('employee_id', 'role', 'phone', 'department', 'plant', 'location', 
                      'is_active_employee', 'date_joined_company'),
            'description': 'Note: Superadmin users are created via "python manage.py createsuperuser" command and do not have a role.'
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('EHS-360 Information', {
            'fields': ('email', 'first_name', 'last_name', 'employee_id', 'role', 'phone'),
            'description': 'Create employee users here. For superadmin, use "python manage.py createsuperuser" command.'
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Automatically set staff status for roles"""
        
        # If is_superuser is checked, it's a superadmin (though should use createsuperuser)
        if obj.is_superuser:
            obj.is_staff = True
            obj.role = 'ADMIN'  # Set default role to avoid null
        
        # ADMIN role - Only EHS-360 web app access, NO Django admin
        elif obj.role == 'ADMIN':
            obj.is_staff = False
            obj.is_superuser = False
        
        # Regular employees - No Django admin access
        else:
            obj.is_staff = False
            obj.is_superuser = False
        
        super().save_model(request, obj, form, change)
        
admin.site.register(Role)
admin.site.register(Permissions)
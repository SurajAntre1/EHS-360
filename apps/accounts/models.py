from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.accidents import *
from apps.organizations.models import *

class User(AbstractUser):
    """Custom User Model for EHS-360"""
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
        ('PREFER_NOT_TO_SAY', 'Prefer not to say'),
    ]
    EMPLOYMENT_TYPE_CHOICES = [
        ('FULL_TIME', 'Full-time'),
        ('PART_TIME', 'Part-time'),
        ('CONTRACT', 'Contract'),
        ('TEMPORARY', 'Temporary'),
        ('INTERN', 'Intern'),
        ('CONSULTANT', 'Consultant'),
    ]
    
    email = models.EmailField(unique=True,null=False,blank=False, verbose_name='Email Address', help_text='User email (must be unique)')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True, verbose_name="Gender")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Date of Birth", help_text="Employee's date of birth")
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='FULL_TIME', verbose_name="Employment Type")
    job_title = models.CharField(max_length=100, null=True, blank=True, verbose_name="Job Title", help_text="Employee's job title/designation")
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    role = models.ForeignKey('Role',on_delete=models.SET_NULL, null=True, blank=True, related_name="role_user")
    phone = models.CharField(max_length=15, blank=True)
    department = models.ForeignKey(
        'organizations.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users'
    )
    
    # ============================================
    # SINGLE ASSIGNMENT (Primary/Default Location)
    # ============================================
    plant = models.ForeignKey(
        'organizations.Plant', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name="Primary Plant",
        help_text="Primary plant assignment"
    )
    zone = models.ForeignKey(
        'organizations.Zone', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name="Primary Zone",
        help_text="Primary zone assignment"
    )
    location = models.ForeignKey(
        'organizations.Location', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name="Primary Location",
        help_text="Primary location assignment"
    )
    sublocation = models.ForeignKey(
        SubLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name="Primary Sub-Location",
        help_text="Primary sub-location assignment"
    )
    
    # ============================================
    # MULTIPLE ASSIGNMENTS (For HOD, Managers, etc.)
    # ============================================
    assigned_plants = models.ManyToManyField(
        'organizations.Plant',
        blank=True,
        related_name='assigned_users_plant',
        verbose_name="Assigned Plants",
        help_text="Multiple plants this user manages/has access to"
    )
    assigned_zones = models.ManyToManyField(
        'organizations.Zone',
        blank=True,
        related_name='assigned_users_zone',
        verbose_name="Assigned Zones",
        help_text="Multiple zones this user manages/has access to"
    )
    assigned_locations = models.ManyToManyField(
        'organizations.Location',
        blank=True,
        related_name='assigned_users_location',
        verbose_name="Assigned Locations",
        help_text="Multiple locations this user manages/has access to"
    )
    assigned_sublocations = models.ManyToManyField(
        'organizations.SubLocation',
        blank=True,
        related_name='assigned_users_sublocation',
        verbose_name="Assigned Sub-Locations",
        help_text="Multiple sub-locations this user manages/has access to"
    )
    
    is_active_employee = models.BooleanField(default=True)
    date_joined_company = models.DateField(null=True, blank=True)
    
    # ============================================
    # MODULE ACCESS PERMISSIONS (Only 5 modules)
    # ============================================
    can_access_incident_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Incident Module",
        help_text="User can report and view incidents"
    )
    can_access_hazard_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Hazard Module",
        help_text="User can report and view hazards"
    )
    can_access_inspection_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Inspection Module",
        help_text="User can conduct safety inspections"
    )
    can_access_reports_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Reports Module",
        help_text="User can view and generate reports"
    )
    can_access_env_data_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Environmental Data Module",
        help_text="User can access and manage environmental data"
    )
    
    # ============================================
    # APPROVAL PERMISSIONS (Only 3 modules)
    # ============================================
    can_approve_incidents = models.BooleanField(
        default=False,
        verbose_name="Can Approve Incidents",
        help_text="User can approve/reject incident reports"
    )
    can_approve_hazards = models.BooleanField(
        default=False,
        verbose_name="Can Approve Hazards",
        help_text="User can approve/reject hazard reports"
    )
    can_approve_inspections = models.BooleanField(
        default=False,
        verbose_name="Can Approve Inspections",
        help_text="User can approve inspection reports"
    )
    
    # ============================================
    # CLOSURE PERMISSIONS (Only 2 modules)
    # ============================================
    can_close_incidents = models.BooleanField(
        default=False,
        verbose_name="Can Close Incidents",
        help_text="User can close completed incidents"
    )
    can_close_hazards = models.BooleanField(
        default=False,
        verbose_name="Can Close Hazards",
        help_text="User can close resolved hazards"
    )
    can_create_users=models.BooleanField(
        default=False,
        verbose_name="can Create Users",
        help_text="Users can create users for their assigned plants only"
    )
 
    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id or self.username})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - self.date_of_birth.year
            if today.month < self.date_of_birth.month or \
            (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
                age -= 1
            return age
        return None

    @property
    def years_in_current_job(self):
        """Calculate years in current job from date_joined_company"""
        if self.date_joined_company:
            from datetime import date
            today = date.today()
            years = today.year - self.date_joined_company.year
            if today.month < self.date_joined_company.month or \
            (today.month == self.date_joined_company.month and today.day < self.date_joined_company.day):
                years -= 1
            
            months = (today.year - self.date_joined_company.year) * 12 + today.month - self.date_joined_company.month
            
            if years > 0:
                return f"{years} year{'s' if years != 1 else ''}"
            elif months > 0:
                return f"{months} month{'s' if months != 1 else ''}"
            else:
                return "Less than a month"
        return None
    
    # ============================================
    # SYNC PERMISSIONS FROM ROLE TO FLAGS
    # ============================================
    def sync_permissions_to_flags(self):
        """Sync role permissions to user's boolean permission fields"""
        if not self.role:
            self._reset_all_permissions()
            self.save()
            return 0
        
        permission_codes = list(self.role.permissions.values_list('code', flat=True))
        
        # Map permission codes to boolean fields
        permission_mapping = {
            # Module Access (5 modules)
            'ACCESS_INCIDENT_MODULE': 'can_access_incident_module',
            'ACCESS_HAZARD_MODULE': 'can_access_hazard_module',
            'ACCESS_INSPECTION_MODULE': 'can_access_inspection_module',
            'ACCESS_REPORTS_MODULE': 'can_access_reports_module',
            'ACCESS_ENV_DATA_MODULE': 'can_access_env_data_module',
            
            # Approvals (3 modules)
            'APPROVE_INCIDENT': 'can_approve_incidents',
            'APPROVE_HAZARD': 'can_approve_hazards',
            'APPROVE_INSPECTION': 'can_approve_inspections',
            
            # Closures (2 modules)
            'CLOSE_INCIDENT': 'can_close_incidents',
            'CLOSE_HAZARD': 'can_close_hazards',
            'CAN_CREATE_USERS':'can_create_users',
        }
        
        self._reset_all_permissions()
        
        updated_count = 0
        for code in permission_codes:
            if code in permission_mapping:
                field_name = permission_mapping[code]
                setattr(self, field_name, True)
                updated_count += 1
        
        self.save()
        return updated_count

    def _reset_all_permissions(self):
        """Helper: Reset all permission flags to False"""
        self.can_access_incident_module = False
        self.can_access_hazard_module = False
        self.can_access_inspection_module = False
        self.can_access_reports_module = False
        self.can_access_env_data_module = False
        self.can_approve_incidents = False
        self.can_approve_hazards = False
        self.can_approve_inspections = False
        self.can_close_incidents = False
        self.can_close_hazards = False
        self.can_create_users=False

    def has_permission(self, code):
        """Check if user has a specific permission by code"""
        if self.is_superuser:
            return True
        if not self.role:
            return False
        return self.role.permissions.filter(code=code).exists()

    @property
    def role_name(self):
        """Get user's role name dynamically"""
        return self.role.name if self.role else None

    @property
    def can_approve(self):
        """Check if user can approve anything"""
        return (
            self.is_superuser or 
            self.can_approve_incidents or 
            self.can_approve_hazards or
            self.can_approve_inspections
        )
    
    # ============================================
    # HELPER METHODS FOR MULTIPLE ASSIGNMENTS
    # ============================================
    def get_all_plants(self):
        """Get all plants (primary + assigned)"""
        plants = list(self.assigned_plants.all())
        if self.plant and self.plant not in plants:
            plants.insert(0, self.plant)
        return plants
    
    def get_all_zones(self):
        """Get all zones (primary + assigned)"""
        zones = list(self.assigned_zones.all())
        if self.zone and self.zone not in zones:
            zones.insert(0, self.zone)
        return zones
    
    def get_all_locations(self):
        """Get all locations (primary + assigned)"""
        locations = list(self.assigned_locations.all())
        if self.location and self.location not in locations:
            locations.insert(0, self.location)
        return locations
    
    def get_all_sublocations(self):
        """Get all sublocations (primary + assigned)"""
        sublocations = list(self.assigned_sublocations.all())
        if self.sublocation and self.sublocation not in sublocations:
            sublocations.insert(0, self.sublocation)
        return sublocations
    
    def has_access_to_plant(self, plant):
        """Check if user has access to a specific plant"""
        return plant == self.plant or plant in self.assigned_plants.all()
    
    def has_access_to_zone(self, zone):
        """Check if user has access to a specific zone"""
        return zone == self.zone or zone in self.assigned_zones.all()
    
    def has_access_to_location(self, location):
        """Check if user has access to a specific location"""
        return location == self.location or location in self.assigned_locations.all()
    
    def has_access_to_sublocation(self, sublocation):
        """Check if user has access to a specific sublocation"""
        return sublocation == self.sublocation or sublocation in self.assigned_sublocations.all()
    
    @property
    def is_superadmin(self):
        """Check if user is superadmin (created via createsuperuser command)"""
        return self.is_superuser
    
    @property
    def is_admin_user(self):
        """Check if user is admin - employee with full EHS-360 access"""
        return self.role and self.role.name == 'ADMIN'
    
    @property
    def is_employee_account(self):
        """Check if this is an employee account (not superadmin)"""
        return not self.is_superuser


class Permissions(models.Model):
    """Permission Master with Module Hierarchy - 5 Modules Only"""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # Only 5 modules
    module = models.CharField(
        max_length=50,
        choices=[
            ('INCIDENT', 'Incident Module'),
            ('HAZARD', 'Hazard Module'),
            ('INSPECTION', 'Inspection Module'),
            ('REPORTS', 'Reports Module'),
            ('ENV_DATA', 'Environmental Data Module'),
        ],
        null=True,
        blank=True,
        help_text="Which module this permission belongs to"
    )
    
    permission_type = models.CharField(
        max_length=20,
        choices=[
            ('MODULE_ACCESS', 'Module Access'),
            ('CREATE', 'Create'),
            ('EDIT', 'Edit'),
            ('VIEW', 'View'),
            ('DELETE', 'Delete'),
            ('APPROVE', 'Approve'),
            ('CLOSE', 'Close'),
            ('MANAGE', 'Manage'),
            ('EXPORT', 'Export'),
        ],
        default='VIEW',
        help_text="Type of permission"
    )
    
    display_order = models.IntegerField(
        default=0,
        help_text="Order to display in UI (lower = first)"
    )
    
    class Meta:
        ordering = ['module', 'display_order', 'code']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_module_access(self):
        """Check if this is a module access permission"""
        return self.permission_type == 'MODULE_ACCESS'


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permissions,
        related_name='roles',
        blank=True
    )

    def __str__(self):
        return self.name
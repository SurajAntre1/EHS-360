from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.accidents import *
from apps.organizations.models import *

class User(AbstractUser):
    """Custom User Model for EHS-360"""
    
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('EMPLOYEE', 'Employee'),
        ('SAFETY_MANAGER', 'Safety Manager'),
        ('LOCATION_HEAD', 'Location Head'),
        ('PLANT_HEAD', 'Plant Head'),
        ('HOD', 'Head of Department'),
    ]
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
    # MODULE ACCESS PERMISSIONS (Can Access/Use)
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
    can_access_audit_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Audit Module",
        help_text="User can perform safety audits"
    )
    can_access_training_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Training Module",
        help_text="User can access training materials"
    )
    can_access_permit_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Permit Module",
        help_text="User can request work permits"
    )
    can_access_observation_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Observation Module",
        help_text="User can submit safety observations"
    )
    can_access_reports_module = models.BooleanField(
        default=False,
        verbose_name="Can Access Reports Module",
        help_text="User can view and generate reports"
    )
    
    # ============================================
    # APPROVAL PERMISSIONS (Can Approve)
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
    can_approve_permits = models.BooleanField(
        default=False,
        verbose_name="Can Approve Permits",
        help_text="User can approve work permit requests"
    )
    
    # ============================================
    # CLOSURE PERMISSIONS
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
            # Adjust if birthday hasn't occurred this year
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
            # Adjust if anniversary hasn't occurred this year
            if today.month < self.date_joined_company.month or \
            (today.month == self.date_joined_company.month and today.day < self.date_joined_company.day):
                years -= 1
            
            # Calculate months for more precision
            months = (today.year - self.date_joined_company.year) * 12 + today.month - self.date_joined_company.month
            
            if years > 0:
                return f"{years} year{'s' if years != 1 else ''}"
            elif months > 0:
                return f"{months} month{'s' if months != 1 else ''}"
            else:
                return "Less than a month"
        return None
    
    # def save(self, *args, **kwargs):
    #     if self.is_superuser:
    #         self.role = self.role or 'ADMIN'
    #         self.is_staff = True
        
    #     # Auto-assign based on role
    #     if self.role == 'ADMIN':
    #         # Admins get all module access
    #         self.can_access_incident_module = True
    #         self.can_access_hazard_module = True
    #         self.can_access_inspection_module = True
    #         self.can_access_audit_module = True
    #         self.can_access_training_module = True
    #         self.can_access_permit_module = True
    #         self.can_access_observation_module = True
    #         self.can_access_reports_module = True
    #         # Admins get all approval permissions
    #         self.can_approve_incidents = True
    #         self.can_approve_hazards = True
    #         self.can_approve_inspections = True
    #         self.can_approve_permits = True
    #         self.can_close_incidents = True
    #         self.can_close_hazards = True
        
    #     elif self.role == 'SAFETY_MANAGER':
    #         # Safety Managers get all module access
    #         self.can_access_incident_module = True
    #         self.can_access_hazard_module = True
    #         self.can_access_inspection_module = True
    #         self.can_access_audit_module = True
    #         self.can_access_reports_module = True
    #         # Safety Managers can approve
    #         self.can_approve_incidents = True
    #         self.can_approve_hazards = True
    #         self.can_approve_inspections = True
    #         self.can_close_incidents = True
    #         self.can_close_hazards = True
        
    #     elif self.role == 'PLANT_HEAD':
    #         # Plant Heads get most modules
    #         self.can_access_incident_module = True
    #         self.can_access_hazard_module = True
    #         self.can_access_inspection_module = True
    #         self.can_access_reports_module = True
    #         # Plant Heads can approve
    #         self.can_approve_incidents = True
    #         self.can_approve_hazards = True
    #         self.can_approve_permits = True
        
    #     elif self.role == 'LOCATION_HEAD':
    #         # Location Heads get basic modules
    #         self.can_access_incident_module = True
    #         self.can_access_hazard_module = True
    #         self.can_access_observation_module = True
    #         # Location Heads can approve hazards
    #         self.can_approve_hazards = True
        
    #     elif self.role == 'HOD':
    #         # HODs get comprehensive access
    #         self.can_access_incident_module = True
    #         self.can_access_hazard_module = True
    #         self.can_access_inspection_module = True
    #         self.can_access_reports_module = True
    #         # HODs can approve
    #         self.can_approve_hazards = True
    #         self.can_approve_inspections = True
        
    #     elif self.role == 'EMPLOYEE':
    #         # Employees get basic reporting modules by default
    #         self.can_access_incident_module = True
    #         self.can_access_hazard_module = True
    #         self.can_access_observation_module = True
    #         self.can_access_training_module = True
        
    #     super().save(*args, **kwargs)
    
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
    
    @property
    def is_safety_manager(self):
        return self.role and self.role.name == 'SAFETY MANAGER'
    
    @property
    def is_location_head(self):
        return self.role and self.role.name == 'LOCATION HEAD'
    
    @property
    def is_plant_head(self):
        return self.role and self.role.name == 'PLANT HEAD'
    
    @property
    def is_hod(self):
        return self.role.name == 'HOD'
    
    @property
    def is_employee(self):
        return self.role.name == 'EMPLOYEE'
    
    @property
    def can_approve(self):
        """Check if user can approve anything"""
        return (
            self.is_superuser or 
            self.can_approve_incidents or 
            self.can_approve_hazards or
            self.can_approve_inspections or
            self.can_approve_permits
        )
    
    def get_accessible_modules(self):
        """Get list of modules user can access"""
        modules = []
        if self.can_access_incident_module:
            modules.append('Incident Management')
        if self.can_access_hazard_module:
            modules.append('Hazard Management')
        if self.can_access_inspection_module:
            modules.append('Safety Inspections')
        if self.can_access_audit_module:
            modules.append('Safety Audits')
        if self.can_access_training_module:
            modules.append('Training')
        if self.can_access_permit_module:
            modules.append('Work Permits')
        if self.can_access_observation_module:
            modules.append('Safety Observations')
        if self.can_access_reports_module:
            modules.append('Reports & Analytics')
        return modules
    
    def get_pending_approvals_count(self):
        """Get total count of pending approvals for this user"""
        from apps.hazards.models import Hazard
        
        count = 0
        
        # Count pending hazards
        if self.can_approve_hazards or self.is_superuser:
            hazards_query = Hazard.objects.filter(
                status='PENDING_APPROVAL',
                approval_status='PENDING'
            )
            if not self.is_superuser and self.plant:
                hazards_query = hazards_query.filter(plant=self.plant)
            count += hazards_query.count()
        
        return count
    
    @property
    def role_display(self):
        if self.is_superuser:
            return "Super Admin"
        if self.role:
            return self.role.name
        return "Employee"
    
    def has_permission(self, code):
        if self.is_superuser:
            return True
        if not self.role:
            return False
        return self.role.permissions.filter(code=code).exists()

class Permissions(models.Model):
    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="System permission code (e.g. REPORT_INCIDENT)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Human readable permission name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the permission"
    )

    def __str__(self):
        return self.code

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permissions,
        related_name='roles'
    )

    def __str__(self):
        return self.name

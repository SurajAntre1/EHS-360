from django.core.management.base import BaseCommand
from apps.accounts.models import Permissions, Role

class Command(BaseCommand):
    help = 'Setup default permissions and roles for EHS-360'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting permission setup...'))
        
        # Step 1: Create Permissions
        self.create_permissions()
        
        # Step 2: Create Roles with Permissions
        self.create_roles()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Permission setup completed successfully!'))
    
    def create_permissions(self):
        """Create all system permissions"""
        self.stdout.write('\n📋 Creating permissions...')
        
        permissions_data = [
            # Incident Permissions
            ('CREATE_INCIDENT', 'Create Incident', 'Can create/report new incidents'),
            ('EDIT_INCIDENT', 'Edit Incident', 'Can edit incident reports'),
            ('DELETE_INCIDENT', 'Delete Incident', 'Can delete incidents'),
            ('VIEW_INCIDENT', 'View Incident', 'Can view incident details'),
            ('APPROVE_INCIDENT', 'Approve Incident', 'Can approve/reject incident reports'),
            ('CLOSE_INCIDENT', 'Close Incident', 'Can close completed incidents'),
            
            # Hazard Permissions
            ('CREATE_HAZARD', 'Create Hazard', 'Can create/report new hazards'),
            ('EDIT_HAZARD', 'Edit Hazard', 'Can edit hazard reports'),
            ('DELETE_HAZARD', 'Delete Hazard', 'Can delete hazards'),
            ('VIEW_HAZARD', 'View Hazard', 'Can view hazard details'),
            ('APPROVE_HAZARD', 'Approve Hazard', 'Can approve/reject hazard reports'),
            ('CLOSE_HAZARD', 'Close Hazard', 'Can close resolved hazards'),
            
            # Inspection Permissions
            ('CREATE_INSPECTION', 'Create Inspection', 'Can create/schedule inspections'),
            ('EDIT_INSPECTION', 'Edit Inspection', 'Can edit inspection reports'),
            ('DELETE_INSPECTION', 'Delete Inspection', 'Can delete inspections'),
            ('VIEW_INSPECTION', 'View Inspection', 'Can view inspection details'),
            ('APPROVE_INSPECTION', 'Approve Inspection', 'Can approve inspection reports'),
            
            # Module Access Permissions
            ('ACCESS_INCIDENT_MODULE', 'Access Incident Module', 'Can access incident management module'),
            ('ACCESS_HAZARD_MODULE', 'Access Hazard Module', 'Can access hazard management module'),
            ('ACCESS_INSPECTION_MODULE', 'Access Inspection Module', 'Can access inspection module'),
            ('ACCESS_AUDIT_MODULE', 'Access Audit Module', 'Can access audit module'),
            ('ACCESS_TRAINING_MODULE', 'Access Training Module', 'Can access training module'),
            ('ACCESS_PERMIT_MODULE', 'Access Permit Module', 'Can access work permit module'),
            ('ACCESS_OBSERVATION_MODULE', 'Access Observation Module', 'Can access safety observation module'),
            ('ACCESS_REPORTS_MODULE', 'Access Reports Module', 'Can access reports and analytics'),
            
            # Other Permissions
            ('APPROVE_PERMIT', 'Approve Permit', 'Can approve work permit requests'),
        ]
        
        for code, name, description in permissions_data:
            perm, created = Permissions.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': description}
            )
            if created:
                self.stdout.write(f'  ✓ Created: {code}')
            else:
                self.stdout.write(f'  - Exists: {code}')
    
    def create_roles(self):
        """Create roles and assign permissions"""
        self.stdout.write('\n👥 Creating roles...')
        
        # ADMIN Role
        self.create_admin_role()
        
        # SAFETY MANAGER Role
        self.create_safety_manager_role()
        
        # HOD Role
        self.create_hod_role()
        
        # PLANT HEAD Role
        self.create_plant_head_role()
        
        # LOCATION HEAD Role
        self.create_location_head_role()
        
        # EMPLOYEE Role
        self.create_employee_role()
    
    def create_admin_role(self):
        """Create ADMIN role with all permissions"""
        role, created = Role.objects.get_or_create(
            name='ADMIN',
            defaults={'description': 'System administrator with full access to all modules'}
        )
        
        if created or True:  # Always update permissions
            # Admin gets ALL permissions
            all_perms = Permissions.objects.all()
            role.permissions.set(all_perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: ADMIN role ({all_perms.count()} permissions)')
    
    def create_safety_manager_role(self):
        """Create SAFETY MANAGER role"""
        role, created = Role.objects.get_or_create(
            name='SAFETY MANAGER',
            defaults={'description': 'Safety manager with approval and closure rights'}
        )
        
        if created or True:
            perm_codes = [
                # Full incident access
                'CREATE_INCIDENT', 'EDIT_INCIDENT', 'VIEW_INCIDENT', 
                'APPROVE_INCIDENT', 'CLOSE_INCIDENT',
                
                # Full hazard access
                'CREATE_HAZARD', 'EDIT_HAZARD', 'VIEW_HAZARD',
                'APPROVE_HAZARD', 'CLOSE_HAZARD',
                
                # Full inspection access
                'CREATE_INSPECTION', 'EDIT_INSPECTION', 'VIEW_INSPECTION',
                'APPROVE_INSPECTION',
                
                # Module access
                'ACCESS_INCIDENT_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_INSPECTION_MODULE', 'ACCESS_AUDIT_MODULE',
                'ACCESS_REPORTS_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: SAFETY MANAGER role ({perms.count()} permissions)')
    
    def create_hod_role(self):
        """Create HOD (Head of Department) role"""
        role, created = Role.objects.get_or_create(
            name='HOD',
            defaults={'description': 'Head of Department with approval rights'}
        )
        
        if created or True:
            perm_codes = [
                # Can create and view
                'CREATE_INCIDENT', 'VIEW_INCIDENT', 'EDIT_INCIDENT',
                'CREATE_HAZARD', 'VIEW_HAZARD', 'EDIT_HAZARD',
                'APPROVE_HAZARD',  # HODs can approve hazards
                
                # Inspection access
                'VIEW_INSPECTION', 'APPROVE_INSPECTION',
                
                # Module access
                'ACCESS_INCIDENT_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_INSPECTION_MODULE', 'ACCESS_REPORTS_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: HOD role ({perms.count()} permissions)')
    
    def create_plant_head_role(self):
        """Create PLANT HEAD role"""
        role, created = Role.objects.get_or_create(
            name='PLANT HEAD',
            defaults={'description': 'Plant head with approval rights for plant operations'}
        )
        
        if created or True:
            perm_codes = [
                # Incident access
                'CREATE_INCIDENT', 'VIEW_INCIDENT', 'EDIT_INCIDENT',
                'APPROVE_INCIDENT',
                
                # Hazard access
                'CREATE_HAZARD', 'VIEW_HAZARD', 'EDIT_HAZARD',
                'APPROVE_HAZARD',
                
                # Inspection and permits
                'VIEW_INSPECTION', 'APPROVE_PERMIT',
                
                # Module access
                'ACCESS_INCIDENT_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_INSPECTION_MODULE', 'ACCESS_PERMIT_MODULE',
                'ACCESS_REPORTS_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: PLANT HEAD role ({perms.count()} permissions)')
    
    def create_location_head_role(self):
        """Create LOCATION HEAD role"""
        role, created = Role.objects.get_or_create(
            name='LOCATION HEAD',
            defaults={'description': 'Location head with basic approval rights'}
        )
        
        if created or True:
            perm_codes = [
                # Basic reporting
                'CREATE_INCIDENT', 'VIEW_INCIDENT',
                'CREATE_HAZARD', 'VIEW_HAZARD', 'APPROVE_HAZARD',
                
                # Module access
                'ACCESS_INCIDENT_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_OBSERVATION_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: LOCATION HEAD role ({perms.count()} permissions)')
    
    def create_employee_role(self):
        """Create EMPLOYEE role"""
        role, created = Role.objects.get_or_create(
            name='EMPLOYEE',
            defaults={'description': 'Regular employee with basic reporting access'}
        )
        
        if created or True:
            perm_codes = [
                # Can only create and view own reports
                'CREATE_INCIDENT', 'VIEW_INCIDENT',
                'CREATE_HAZARD', 'VIEW_HAZARD',
                
                # Module access
                'ACCESS_INCIDENT_MODULE', 'ACCESS_HAZARD_MODULE',
                'ACCESS_OBSERVATION_MODULE', 'ACCESS_TRAINING_MODULE',
            ]
            perms = Permissions.objects.filter(code__in=perm_codes)
            role.permissions.set(perms)
            self.stdout.write(f'  ✓ {"Created" if created else "Updated"}: EMPLOYEE role ({perms.count()} permissions)')
from django.db import models
from django.core.exceptions import ValidationError

# apps/organizations/models.py

class Plant(models.Model):
    """Manufacturing Plant/Unit"""
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    contact_person = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Plant'
        verbose_name_plural = 'Plants'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        if self.code:
            self.code = self.code.upper()
    
    @property
    def zone_count(self):
        return self.zones.count()
    
    @property
    def active_zone_count(self):
        return self.zones.filter(is_active=True).count()
    
    @property
    def location_count(self):
        """Get count of all locations through zones"""
        from django.db.models import Count
        return Location.objects.filter(zone__plant=self).count()
    
    @property
    def active_location_count(self):
        """Get count of active locations through zones"""
        return Location.objects.filter(zone__plant=self, is_active=True).count()
    
    @property
    def sublocation_count(self):
        """Get count of all sublocations through zones and locations"""
        from .models import SubLocation
        return SubLocation.objects.filter(location__zone__plant=self).count()
    
    @property
    def active_sublocation_count(self):
        """Get count of active sublocations through zones and locations"""
        from .models import SubLocation
        return SubLocation.objects.filter(location__zone__plant=self, is_active=True).count()

class Zone(models.Model):
    """Zones within a Plant (e.g., Zone A, Zone B)"""
    
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['plant', 'name']
        unique_together = ['plant', 'code']
        verbose_name = 'Zone'
        verbose_name_plural = 'Zones'
    
    def __str__(self):
        return f"{self.plant.name} - {self.name}"
    
    def clean(self):
        # Convert code to uppercase
        if self.code:
            self.code = self.code.upper()
    
    @property
    def location_count(self):
        return self.locations.count()
    
    @property
    def active_location_count(self):
        return self.locations.filter(is_active=True).count()


class Location(models.Model):
    """Locations within a Zone"""
    
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['zone', 'name']
        unique_together = ['zone', 'code']
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
    
    def __str__(self):
        return f"{self.zone.plant.name} - {self.zone.name} - {self.name}"
    
    def clean(self):
        # Convert code to uppercase
        if self.code:
            self.code = self.code.upper()
    
    @property
    def plant(self):
        """Get the plant through zone"""
        return self.zone.plant

class SubLocation(models.Model):
    """Sub-locations within a Location"""
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='sublocations')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50,blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['location', 'name']
        verbose_name = 'Sub-Location'
        verbose_name_plural = 'Sub-Locations'
    
    def __str__(self):
        return f"{self.location.zone.plant.name} - {self.location.zone.name} - {self.location.name} - {self.name}"
    
    def clean(self):
        # Convert code to uppercase
        if self.code:
            self.code = self.code.upper()
    
    @property
    def plant(self):
        """Get the plant through location -> zone"""
        return self.location.zone.plant
    
    @property
    def zone(self):
        """Get the zone through location"""
        return self.location.zone
class Department(models.Model):
    """Departments within organization"""
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    head_name = models.CharField(max_length=100, blank=True, help_text="Department Head Name")
    head_email = models.EmailField(blank=True, help_text="Department Head Email")
    head_phone = models.CharField(max_length=15, blank=True, help_text="Department Head Phone")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def clean(self):
        # Convert code to uppercase
        if self.code:
            self.code = self.code.upper()
    
    @property
    def employee_count(self):
        return self.users.count()
    
    @property
    def active_employee_count(self):
        return self.users.filter(is_active=True).count()
# apps/hazards/apps.py

from django.apps import AppConfig

from django.apps import AppConfig

class HazardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hazards'
    
    def ready(self):
        import apps.hazards.signals  # ✅ Register signals
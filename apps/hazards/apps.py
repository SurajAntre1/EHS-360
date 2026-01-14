# apps/hazards/apps.py

from django.apps import AppConfig

class HazardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hazards'

    def ready(self):
        """
        This method is called when the application is ready.
        We import the signals module here to ensure that the signal handlers
        are registered with Django's signal dispatcher.
        """
        import apps.hazards.signals  
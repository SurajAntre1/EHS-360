from django.apps import AppConfig


class EnvdataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ENVdata'
    def ready(self):
        from .seed import seed_environmental_questions
        seed_environmental_questions()
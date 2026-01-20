from django.db.utils import OperationalError, ProgrammingError

def seed_environmental_questions():
    try:
        from .models import EnvironmentalQuestion
        for index, text in enumerate(EnvironmentalQuestion.PREDEFINED_ENV_QUESTIONS,start=1):
            EnvironmentalQuestion.objects.get_or_create(
                question_text=text,
                defaults={"is_system": True,"order": index,"is_active": True,})

    except (OperationalError, ProgrammingError):
        pass

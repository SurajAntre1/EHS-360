import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ehs360_project.settings')

app = Celery('ehs360_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks for email notifications
app.conf.beat_schedule = {
    'check-due-date-reminders': {
        'task': 'apps.notifications.tasks.send_due_date_reminders',
        'schedule': crontab(hour=9, minute=0),  # Run daily at 9 AM
    },
    'check-overdue-escalations': {
        'task': 'apps.notifications.tasks.send_overdue_escalations',
        'schedule': crontab(hour=10, minute=0),  # Run daily at 10 AM
    },
    'check-investigation-overdue': {
    'task': 'apps.notifications.tasks.send_investigation_overdue_notifications',
    'schedule': crontab(hour=11, minute=0),  # Daily at 8 AM IST
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
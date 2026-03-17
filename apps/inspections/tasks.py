# apps/inspections/tasks.py

from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def auto_create_monthly_inspection_schedules(self):
    """
    Runs on 1st of every month.
    For each active, non-paused TemplateAutoScheduleConfig:
    - Creates one InspectionSchedule per assigned user
    - Skips if schedule already exists for this month + template + user
    - Sends notification to each assigned user
    """
    from .models import (
        TemplateAutoScheduleConfig,
        InspectionSchedule,
    )
    from apps.notifications.services import NotificationService

    now = timezone.now()
    current_month_start = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    current_month_end = (
        current_month_start.replace(month=current_month_start.month % 12 + 1)
        if current_month_start.month < 12
        else current_month_start.replace(
            year=current_month_start.year + 1, month=1
        )
    )

    logger.info(
        f"[AutoSchedule] Running for {current_month_start.strftime('%B %Y')}"
    )

    # Get all active, non-paused configs
    configs = TemplateAutoScheduleConfig.objects.filter(
        is_active=True,
        is_paused=False
    ).prefetch_related(
        'plants',
        'zones',
        'locations',
        'sublocations',
        'assigned_users',
        'assigned_users__role',
        'template'
    )

    total_created = 0
    total_skipped = 0
    total_errors = 0

    for config in configs:
        try:
            # Skip if template is inactive
            if not config.template.is_active:
                logger.warning(
                    f"[AutoSchedule] Skipping config {config.id} — "
                    f"template {config.template.template_code} is inactive"
                )
                continue

            assigned_users = config.assigned_users.filter(
                is_active=True,
                is_active_employee=True
            )

            if not assigned_users.exists():
                logger.warning(
                    f"[AutoSchedule] Config {config.id} has no active users. Skipping."
                )
                continue

            plants = config.plants.filter(is_active=True)
            if not plants.exists():
                logger.warning(
                    f"[AutoSchedule] Config {config.id} has no active plants. Skipping."
                )
                continue

            # Scheduled date = 1st of current month
            scheduled_date = current_month_start.date()

            # Due date = scheduled date + offset days
            due_date = scheduled_date + timezone.timedelta(
                days=config.due_date_offset_days
            )

            for user in assigned_users:
                try:
                    with transaction.atomic():
                        # Check if schedule already exists for this
                        # month + template + user to avoid duplicates
                        already_exists = InspectionSchedule.objects.filter(
                            template=config.template,
                            assigned_to=user,
                            scheduled_date__gte=current_month_start.date(),
                            scheduled_date__lt=current_month_end.date(),
                        ).exists()

                        if already_exists:
                            logger.info(
                                f"[AutoSchedule] Schedule already exists for "
                                f"user {user.get_full_name()} | "
                                f"template {config.template.template_code} | "
                                f"month {current_month_start.strftime('%B %Y')}. Skipping."
                            )
                            total_skipped += 1
                            continue

                        # Create schedule
                        schedule = InspectionSchedule(
                            template=config.template,
                            assigned_to=user,
                            assigned_by=None,  # system-created
                            scheduled_date=scheduled_date,
                            due_date=due_date,
                            status='SCHEDULED',
                            assignment_notes=(
                                f"Auto-created by system for "
                                f"{current_month_start.strftime('%B %Y')}"
                            )
                        )
                        schedule.save()

                        # Set M2M
                        schedule.plants.set(plants)
                        schedule.zones.set(config.zones.all())
                        schedule.locations.set(config.locations.all())
                        schedule.sublocations.set(config.sublocations.all())
                        schedule.assigned_users.set(assigned_users)

                        total_created += 1
                        logger.info(
                            f"[AutoSchedule] Created {schedule.schedule_code} "
                            f"for {user.get_full_name()}"
                        )

                        # Send notification
                        try:
                            NotificationService.notify(
                                content_object=schedule,
                                notification_type='INSPECTION_SCHEDULE',
                                module='INSPECTION'
                            )
                        except Exception as notif_error:
                            logger.error(
                                f"[AutoSchedule] Notification error for "
                                f"{schedule.schedule_code}: {notif_error}"
                            )

                except Exception as user_error:
                    total_errors += 1
                    logger.error(
                        f"[AutoSchedule] Error creating schedule for user "
                        f"{user.get_full_name()} | config {config.id}: {user_error}"
                    )
                    continue

        except Exception as config_error:
            total_errors += 1
            logger.error(
                f"[AutoSchedule] Error processing config {config.id}: {config_error}"
            )
            continue

    logger.info(
        f"[AutoSchedule] Done. "
        f"Created: {total_created} | "
        f"Skipped: {total_skipped} | "
        f"Errors: {total_errors}"
    )

    return {
        'created': total_created,
        'skipped': total_skipped,
        'errors': total_errors,
        'month': current_month_start.strftime('%B %Y')
    }
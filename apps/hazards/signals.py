# apps/hazards/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import HazardActionItem

@receiver(post_save, sender=HazardActionItem)
def update_hazard_status_on_action_item_save(sender, instance, created, **kwargs):
    """
    Update hazard status when action item is created or updated,
    but only if hazard is already approved
    """
    hazard = instance.hazard
    
    # Only update if hazard is in post-approval stages
    if hazard.status not in ['REPORTED', 'PENDING_APPROVAL', 'CLOSED', 'REJECTED']:
        hazard.update_status_from_action_items()


@receiver(post_delete, sender=HazardActionItem)
def update_hazard_status_on_action_delete(sender, instance, **kwargs):
    """
    Signal receiver triggered after a HazardActionItem is deleted.

    This is crucial for scenarios where deleting the last action item should
    revert the hazard's status back to a previous state (e.g., 'APPROVED').
    """
    if instance.hazard:
        instance.hazard.update_status_from_action_items()
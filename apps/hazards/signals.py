# apps/hazards/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import HazardActionItem

@receiver(post_save, sender=HazardActionItem)
def update_hazard_status_on_action_save(sender, instance, **kwargs):
    """
    Signal receiver triggered after a HazardActionItem is saved.
    
    This function calls the parent hazard's method to re-evaluate and update its status
    based on the collective status of all its action items.
    """
    if instance.hazard:
        instance.hazard.update_status_from_action_items()


@receiver(post_delete, sender=HazardActionItem)
def update_hazard_status_on_action_delete(sender, instance, **kwargs):
    """
    Signal receiver triggered after a HazardActionItem is deleted.

    This is crucial for scenarios where deleting the last action item should
    revert the hazard's status back to a previous state (e.g., 'APPROVED').
    """
    if instance.hazard:
        instance.hazard.update_status_from_action_items()
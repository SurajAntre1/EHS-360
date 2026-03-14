from .models import HazardActionItem
from apps.accidents.models import IncidentActionItem

def hazard_action_items_count(request):
    count = 0

    if request.user.is_authenticated and request.user.email:
        count = HazardActionItem.objects.filter(
            responsible_emails__icontains=request.user.email
        ).count()

    return {
        "my_pending_actions_count": count
    }

def incident_action_items_count(request):
    count = 0

    if request.user.is_authenticated and request.user.email:
        count = IncidentActionItem.objects.filter(
            responsible_person=request.user
        ).count()

    return {
        "my_pending_incidents_actions_count": count
    }
        
from django import template

register = template.Library()

@register.filter
def get_location_names(zone, limit=3):
    """Get comma-separated location names with limit"""
    locations = zone.locations.all()[:limit]
    names = [loc.code for loc in locations]
    
    if zone.locations.count() > limit:
        names.append(f"+{zone.locations.count() - limit} more")
    
    return ", ".join(names)

@register.filter
def get_sublocation_names(location):
    """Get comma-separated sublocation codes/names"""
    sublocations = location.sublocations.all()
    return ", ".join([subloc.code or subloc.name for subloc in sublocations])
from django import template

register = template.Library()

@register.filter
def abs(value):
    """Return absolute value of a number"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def absolute(value):
    """Return absolute value of a number (alias)"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value
    

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get item from dictionary by key
    Usage: {{ dict|get_item:"key" }}
    """
    if not dictionary:
        return ''
    
    if not isinstance(dictionary, dict):
        return ''
    
    return dictionary.get(key, '')    
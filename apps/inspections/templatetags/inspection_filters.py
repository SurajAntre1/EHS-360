# apps/inspections/templatetags/inspection_filters.py

from django import template

register = template.Library()


@register.filter
def abs_value(value):
    """Returns the absolute value of a number"""
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return value


@register.filter
def subtract(value, arg):
    """Subtracts arg from value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return ''


@register.filter
def multiply(value, arg):
    """Multiplies value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter
def divide(value, arg):
    """Divides value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''


@register.filter
def percentage(value, total):
    """Calculates percentage of value out of total"""
    try:
        return round((float(value) / float(total)) * 100, 2)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
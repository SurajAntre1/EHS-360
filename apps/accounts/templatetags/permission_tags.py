from django import template

register = template.Library()

@register.filter
def has_perm(user, permission_code):
    """Check if user has a specific permission by code"""
    if user.is_superuser:
        return True
    if not user.role:
        return False
    return user.role.permissions.filter(code=permission_code).exists()
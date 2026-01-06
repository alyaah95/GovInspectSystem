from django import template

register = template.Library()

@register.filter
def is_manager(user):
    return user.groups.filter(name='Managers').exists()

@register.filter
def is_inspector(user):
    return user.groups.filter(name='Inspectors').exists()
from django import template

from core.formatters import format_cpf, format_phone


register = template.Library()


@register.filter
def cpf_mask(value):
    return format_cpf(value)


@register.filter
def phone_mask(value):
    return format_phone(value)

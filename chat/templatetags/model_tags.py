from django import template
from chat.model_config import get_models_for_template, get_all_models

register = template.Library()

@register.inclusion_tag('chat/model_options.html')
def model_options():
    """Возвращает опции моделей для select."""
    return {'models': get_models_for_template()}

@register.simple_tag
def get_all_models_list():
    """Возвращает список всех моделей."""
    return get_all_models()

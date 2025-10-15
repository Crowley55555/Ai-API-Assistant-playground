"""
Конфигурация доступных моделей ИИ.
"""

AVAILABLE_MODELS = {
    'gigachat': [
        {
            'value': 'GigaChat:latest',
            'label': 'GigaChat Latest',
            'description': 'Последняя версия GigaChat'
        },
        {
            'value': 'GigaChat-Pro:latest',
            'label': 'GigaChat Pro',
            'description': 'Профессиональная версия GigaChat'
        },
    ],
    'yandex': [
        {
            'value': 'yandexgpt',
            'label': 'Yandex GPT',
            'description': 'Основная модель Yandex GPT'
        },
        {
            'value': 'yandexgpt-lite',
            'label': 'Yandex GPT Lite',
            'description': 'Облегченная версия Yandex GPT'
        },
    ],
}

def get_models_for_template():
    """Возвращает модели в формате для шаблонов."""
    result = {}
    for provider, models in AVAILABLE_MODELS.items():
        result[provider] = [
            {
                'value': model['value'],
                'label': model['label']
            }
            for model in models
        ]
    return result

def get_all_models():
    """Возвращает все модели в плоском списке."""
    all_models = []
    for provider, models in AVAILABLE_MODELS.items():
        for model in models:
            all_models.append({
                'value': model['value'],
                'label': model['label'],
                'provider': provider,
                'description': model['description']
            })
    return all_models

def get_model_info(model_value):
    """Возвращает информацию о конкретной модели."""
    for provider, models in AVAILABLE_MODELS.items():
        for model in models:
            if model['value'] == model_value:
                return {
                    'value': model['value'],
                    'label': model['label'],
                    'provider': provider,
                    'description': model['description']
                }
    return None

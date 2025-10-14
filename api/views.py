from django.http import JsonResponse
from django.conf import settings
from chat.models import ChatSession, Message


def get_available_models(request):
    """API endpoint для получения доступных моделей."""
    return JsonResponse({
        'models': settings.AVAILABLE_MODELS
    })


def get_sessions(request):
    """API endpoint для получения списка сессий."""
    sessions = ChatSession.objects.all()[:20]  # Последние 20 сессий
    sessions_data = []
    
    for session in sessions:
        sessions_data.append({
            'id': str(session.id),
            'session_id': session.session_id,
            'title': session.title or 'Безымянная сессия',
            'model': session.model,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
            'message_count': session.messages.count(),
        })
    
    return JsonResponse({
        'sessions': sessions_data
    })


def get_token_stats(request):
    """API endpoint для получения статистики токенов."""
    # Общая статистика по всем сессиям
    total_sessions = ChatSession.objects.count()
    total_messages = Message.objects.count()
    
    # Агрегированная статистика токенов
    from django.db.models import Sum
    token_stats = Message.objects.aggregate(
        total_input_tokens=Sum('input_tokens'),
        total_output_tokens=Sum('output_tokens'),
        total_tokens=Sum('total_tokens'),
        total_cost=Sum('estimated_cost')
    )
    
    # Статистика по моделям
    model_stats = {}
    for session in ChatSession.objects.all():
        model = session.model
        if model not in model_stats:
            model_stats[model] = {
                'sessions': 0,
                'total_tokens': 0,
                'total_cost': 0
            }
        model_stats[model]['sessions'] += 1
        model_stats[model]['total_tokens'] += session.total_tokens
        model_stats[model]['total_cost'] += float(session.total_estimated_cost)
    
    return JsonResponse({
        'overview': {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'total_input_tokens': token_stats['total_input_tokens'] or 0,
            'total_output_tokens': token_stats['total_output_tokens'] or 0,
            'total_tokens': token_stats['total_tokens'] or 0,
            'total_cost': float(token_stats['total_cost'] or 0),
        },
        'by_model': model_stats
    })

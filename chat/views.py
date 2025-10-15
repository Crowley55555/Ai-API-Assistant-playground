import json
import uuid
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import ChatSession, Message, UploadedFile, Agent
from .llm_service import LLMService
from .file_processor import FileProcessor

# Настройка логирования
logger = logging.getLogger(__name__)


def playground(request):
    """Основной интерфейс playground."""
    session_id = request.session.get('current_session_id')
    session = None
    
    if session_id:
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            pass
    
    return render(request, 'chat/playground.html', {'session': session})


def history(request):
    """Страница истории чатов."""
    sessions = ChatSession.objects.all()[:50]  # Последние 50 сессий
    return render(request, 'chat/history.html', {'sessions': sessions})


def token_stats(request):
    """Страница статистики токенов."""
    return render(request, 'chat/token_stats.html')


def load_session(request, session_id):
    """Загрузка конкретной сессии."""
    session = get_object_or_404(ChatSession, id=session_id)
    request.session['current_session_id'] = session.session_id
    return render(request, 'chat/playground.html', {'session': session})


def test_connection(request):
    """Страница для тестирования подключения."""
    return render(request, 'chat/test_connection.html')


def csrf_test(request):
    """Страница для тестирования CSRF токена."""
    return render(request, 'chat/csrf_test.html')


def csrf_simple(request):
    """Простая страница для тестирования CSRF токена."""
    return render(request, 'chat/csrf_simple.html')


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Проверка состояния сервера."""
    try:
        return JsonResponse({
            'status': 'ok',
            'message': 'Сервер работает',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    """Создание новой сессии чата."""
    try:
        data = json.loads(request.body)
        session_id = str(uuid.uuid4())
        
        session = ChatSession.objects.create(
            session_id=session_id,
            model=data.get('model', 'llama-3.1-sonar-small-128k-online'),
            temperature=float(data.get('temperature', 0.7)),
            top_p=float(data.get('top_p', 1.0)),
            max_tokens=int(data.get('max_tokens', 4000)),
            system_prompt=data.get('system_prompt', ''),
        )
        
        request.session['current_session_id'] = session_id
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'session': {
                'id': str(session.id),
                'session_id': session.session_id,
                'model': session.model,
                'temperature': session.temperature,
                'top_p': session.top_p,
                'system_prompt': session.system_prompt,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Отправка сообщения в чат."""
    try:
        logger.info("Получен запрос на отправку сообщения")
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            logger.error("Session ID не предоставлен")
            return JsonResponse({'success': False, 'error': 'Session ID required'})
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
            logger.info(f"Найдена сессия: {session_id}")
        except ChatSession.DoesNotExist:
            logger.error(f"Сессия не найдена: {session_id}")
            return JsonResponse({'success': False, 'error': 'Session not found'})
        
        user_message = data.get('message', '').strip()
        if not user_message:
            logger.error("Пустое сообщение")
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        logger.info(f"Сохраняем сообщение пользователя: {user_message[:100]}...")
        # Сохраняем сообщение пользователя
        user_msg = Message.objects.create(
            session=session,
            role='user',
            content=user_message
        )
        
        # Получаем контекст из загруженных файлов
        context = ""
        for file in session.files.all():
            if file.content_preview:
                context += f"\n\nКонтекст из файла {file.filename}:\n{file.content_preview}"
        
        logger.info(f"Модель: {session.model}, температура: {session.temperature}, top_p: {session.top_p}")
        logger.info("Отправляем запрос к LLM сервису")
        
        # Подготавливаем системный промпт с учетом всех настроек
        settings_prompt = f"\n\nКРИТИЧЕСКИ ВАЖНО - СТРОГО СОБЛЮДАЙ:\n"
        settings_prompt += f"МАКСИМУМ ТОКЕНОВ: {session.max_tokens} (НЕ ПРЕВЫШАЙ!)\n"
        
        if session.temperature <= 0.3:
            settings_prompt += f"СТИЛЬ: ОЧЕНЬ КРАТКО! 1-2 предложения. БЕЗ ДЕТАЛЕЙ!\n"
        elif session.temperature <= 0.7:
            settings_prompt += f"СТИЛЬ: Умеренно, с примерами, но без лишнего.\n"
        else:
            settings_prompt += f"СТИЛЬ: Развернуто, с деталями и эмоциями.\n"
            
        if session.top_p <= 0.5:
            settings_prompt += f"ПОДХОД: Только факты, проверенная информация.\n"
        else:
            settings_prompt += f"ПОДХОД: Креативно, нестандартные идеи.\n"
            
        # Добавляем пример для низкой температуры
        if session.temperature <= 0.3:
            settings_prompt += f"\nПРИМЕР КРАТКОГО ОТВЕТА: 'Кот по имени Барсик жил в доме. Он любил спать на солнце.'\n"
            
        system_content = session.system_prompt + context + settings_prompt
        
        # Отправляем запрос к LLM
        llm_service = LLMService()
        response_data = llm_service.generate_response(
            model=session.model,
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': user_message}
            ],
            temperature=session.temperature,
            top_p=session.top_p,
            max_tokens=session.max_tokens
        )
        
        logger.info("Получен ответ от LLM сервиса")
        
        # Сохраняем ответ ассистента с информацией о токенах
        assistant_msg = Message.objects.create(
            session=session,
            role='assistant',
            content=response_data['content'],
            input_tokens=response_data['input_tokens'],
            output_tokens=response_data['output_tokens'],
            total_tokens=response_data['total_tokens'],
            estimated_cost=response_data['cost']['total_cost'],
            metadata={
                'model': session.model,
                'token_stats': {
                    'input_tokens': response_data['input_tokens'],
                    'output_tokens': response_data['output_tokens'],
                    'total_tokens': response_data['total_tokens'],
                    'cost': response_data['cost']
                }
            }
        )
        
        # Обновляем статистику токенов сессии
        session.update_token_stats()
        
        logger.info("Сообщение успешно обработано и сохранено")
        
        return JsonResponse({
            'success': True,
            'user_message': {
                'id': str(user_msg.id),
                'content': user_msg.content,
                'timestamp': user_msg.timestamp.isoformat(),
            },
            'assistant_message': {
                'id': str(assistant_msg.id),
                'content': assistant_msg.content,
                'timestamp': assistant_msg.timestamp.isoformat(),
                'token_stats': {
                    'input_tokens': assistant_msg.input_tokens,
                    'output_tokens': assistant_msg.output_tokens,
                    'total_tokens': assistant_msg.total_tokens,
                    'estimated_cost': float(assistant_msg.estimated_cost),
                }
            },
            'session_stats': session.get_token_stats()
        })
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    """Загрузка файла для сессии."""
    try:
        session_id = request.POST.get('session_id')
        if not session_id:
            return JsonResponse({'success': False, 'error': 'Session ID required'})
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
        
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file provided'})
        
        file = request.FILES['file']
        
        # Обрабатываем файл
        processor = FileProcessor()
        file_type, content_preview = processor.process_file(file)
        
        # Сохраняем файл
        uploaded_file = UploadedFile.objects.create(
            session=session,
            file=file,
            filename=file.name,
            file_type=file_type,
            file_size=file.size,
            content_preview=content_preview
        )
        
        return JsonResponse({
            'success': True,
            'file': {
                'id': str(uploaded_file.id),
                'filename': uploaded_file.filename,
                'file_type': uploaded_file.file_type,
                'file_size': uploaded_file.file_size,
                'content_preview': uploaded_file.content_preview[:500] + '...' if len(uploaded_file.content_preview) > 500 else uploaded_file.content_preview,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Agent views
def agents_list(request):
    """Страница со списком всех агентов."""
    agents = Agent.objects.filter(is_active=True)
    return render(request, 'chat/agents_list.html', {'agents': agents})


def agent_detail(request, agent_id):
    """Страница конкретного агента с чатом."""
    agent = get_object_or_404(Agent, id=agent_id, is_active=True)
    session = agent.get_or_create_session()
    
    # Загружаем сообщения сессии
    messages = session.messages.all()
    
    return render(request, 'chat/agent_detail.html', {
        'agent': agent,
        'session': session,
        'messages': messages
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_agent(request, agent_id):
    """Получение данных агента."""
    try:
        agent = get_object_or_404(Agent, id=agent_id, is_active=True)
        session = agent.get_or_create_session()
        
        # Загружаем последние сообщения
        messages = session.messages.all().order_by('created_at')[:50]
        
        return JsonResponse({
            'success': True,
            'agent': {
                'id': str(agent.id),
                'name': agent.name,
                'description': agent.description,
                'model': agent.model,
                'temperature': agent.temperature,
                'top_p': agent.top_p,
                'system_prompt': agent.system_prompt,
            },
            'messages': [{
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
            } for msg in messages]
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def create_agent(request):
    """Создание нового агента или обновление существующего."""
    try:
        data = json.loads(request.body)
        agent_name = data.get('name', 'Новый агент')
        
        # Проверяем, существует ли уже ассистент с таким именем
        existing_agent = Agent.objects.filter(name=agent_name, is_active=True).first()
        
        if existing_agent:
            # Обновляем существующего ассистента
            existing_agent.description = data.get('description', existing_agent.description)
            existing_agent.model = data.get('model', existing_agent.model)
            existing_agent.temperature = float(data.get('temperature', existing_agent.temperature))
            existing_agent.top_p = float(data.get('top_p', existing_agent.top_p))
            existing_agent.max_tokens = int(data.get('max_tokens', existing_agent.max_tokens))
            existing_agent.system_prompt = data.get('system_prompt', existing_agent.system_prompt)
            existing_agent.updated_at = timezone.now()
            existing_agent.save()
            
            return JsonResponse({
                'success': True,
                'agent': {
                    'id': str(existing_agent.id),
                    'name': existing_agent.name,
                    'description': existing_agent.description,
                    'model': existing_agent.model,
                    'temperature': existing_agent.temperature,
                    'top_p': existing_agent.top_p,
                    'system_prompt': existing_agent.system_prompt,
                    'created_at': existing_agent.created_at.isoformat(),
                },
                'updated': True
            })
        else:
            # Создаем нового ассистента
            agent = Agent.objects.create(
                name=agent_name,
                description=data.get('description', ''),
                model=data.get('model', 'GigaChat:latest'),
                temperature=float(data.get('temperature', 0.7)),
                top_p=float(data.get('top_p', 1.0)),
                max_tokens=int(data.get('max_tokens', 4000)),
                system_prompt=data.get('system_prompt', ''),
            )
            
            return JsonResponse({
                'success': True,
                'agent': {
                    'id': str(agent.id),
                    'name': agent.name,
                    'description': agent.description,
                    'model': agent.model,
                    'temperature': agent.temperature,
                    'top_p': agent.top_p,
                    'system_prompt': agent.system_prompt,
                    'created_at': agent.created_at.isoformat(),
                },
                'updated': False
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def check_agent_exists(request):
    """Проверка существования ассистента по имени."""
    try:
        data = json.loads(request.body)
        agent_name = data.get('name', '')
        
        existing_agent = Agent.objects.filter(name=agent_name, is_active=True).first()
        
        if existing_agent:
            return JsonResponse({
                'exists': True,
                'agent': {
                    'id': str(existing_agent.id),
                    'name': existing_agent.name,
                    'description': existing_agent.description,
                    'model': existing_agent.model,
                    'temperature': existing_agent.temperature,
                    'top_p': existing_agent.top_p,
                    'system_prompt': existing_agent.system_prompt,
                }
            })
        else:
            return JsonResponse({'exists': False})
    except Exception as e:
        return JsonResponse({'exists': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def update_agent(request, agent_id):
    """Обновление агента."""
    try:
        agent = get_object_or_404(Agent, id=agent_id)
        data = json.loads(request.body)
        
        agent.name = data.get('name', agent.name)
        agent.description = data.get('description', agent.description)
        agent.model = data.get('model', agent.model)
        agent.temperature = float(data.get('temperature', agent.temperature))
        agent.top_p = float(data.get('top_p', agent.top_p))
        agent.system_prompt = data.get('system_prompt', agent.system_prompt)
        agent.save()
        
        return JsonResponse({
            'success': True,
            'agent': {
                'id': str(agent.id),
                'name': agent.name,
                'description': agent.description,
                'model': agent.model,
                'temperature': agent.temperature,
                'top_p': agent.top_p,
                'system_prompt': agent.system_prompt,
                'updated_at': agent.updated_at.isoformat(),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def delete_agent(request, agent_id):
    """Удаление агента."""
    try:
        agent = get_object_or_404(Agent, id=agent_id)
        agent.is_active = False
        agent.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def agent_new_session(request, agent_id):
    """Создание новой сессии для агента."""
    try:
        agent = get_object_or_404(Agent, id=agent_id)
        session = agent.create_new_session()
        
        return JsonResponse({
            'success': True,
            'session': {
                'id': str(session.id),
                'session_id': session.session_id,
                'title': session.title,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

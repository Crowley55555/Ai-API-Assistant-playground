import json
import uuid
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import ChatSession, Message, UploadedFile, Agent
from .llm_service import LLMService
from .file_processor import FileProcessor


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
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'success': False, 'error': 'Session ID required'})
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
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
        
        # Отправляем запрос к LLM
        llm_service = LLMService()
        response_data = llm_service.generate_response(
            model=session.model,
            messages=[
                {'role': 'system', 'content': session.system_prompt + context},
                {'role': 'user', 'content': user_message}
            ],
            temperature=session.temperature,
            top_p=session.top_p
        )
        
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
@require_http_methods(["POST"])
def create_agent(request):
    """Создание нового агента."""
    try:
        data = json.loads(request.body)
        
        agent = Agent.objects.create(
            name=data.get('name', 'Новый агент'),
            description=data.get('description', ''),
            model=data.get('model', 'llama-3.1-sonar-small-128k-online'),
            temperature=float(data.get('temperature', 0.7)),
            top_p=float(data.get('top_p', 1.0)),
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
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


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

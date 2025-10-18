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
from .models import ChatSession, Message, UploadedFile, Agent, PythonFunction
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
            model=data.get('model', 'GigaChat:latest'),
            temperature=float(data.get('temperature', 0.7)),
            top_p=float(data.get('top_p', 1.0)),
            max_tokens=int(data.get('max_tokens', 4000)),
            system_prompt=data.get('system_prompt', ''),
            web_search=bool(data.get('web_search', False)),
        )
        
        # Обрабатываем функции если они переданы (просто логируем)
        functions = data.get('functions', [])
        if functions:
            logger.info(f"Функции для сессии {session_id}: {[f.get('name', 'unnamed') for f in functions]}")
        
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
            
            # Проверяем количество сообщений в сессии
            message_count = session.messages.count()
            logger.info(f"Количество сообщений в сессии: {message_count}")
            
        except ChatSession.DoesNotExist:
            logger.error(f"Сессия не найдена: {session_id}")
            return JsonResponse({'success': False, 'error': 'Session not found'})
        
        user_message = data.get('message', '').strip()
        if not user_message:
            logger.error("Пустое сообщение")
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        # Получаем функции из запроса
        functions = data.get('functions', [])
        
        logger.info(f"Сохраняем сообщение пользователя: {user_message[:100]}...")
        # Сохраняем сообщение пользователя
        user_msg = Message.objects.create(
            session=session,
            role='user',
            content=user_message
        )
        
        # Получаем и обрабатываем файлы для обучения
        training_files = []
        processor = FileProcessor()
        
        for uploaded_file in session.files.all():
            try:
                # Обрабатываем файл для обучения
                file_data = processor.process_file_for_training(uploaded_file.file)
                if 'error' not in file_data:
                    file_data['filename'] = uploaded_file.filename
                    training_files.append(file_data)
                else:
                    logger.warning(f"Ошибка обработки файла {uploaded_file.filename}: {file_data['error']}")
            except Exception as e:
                logger.error(f"Ошибка при обработке файла {uploaded_file.filename}: {str(e)}")
        
        # Получаем контекст из загруженных файлов (для обратной совместимости)
        context = ""
        for file in session.files.all():
            if file.content_preview:
                context += f"\n\nКонтекст из файла {file.filename}:\n{file.content_preview}"
        
        logger.info(f"Модель: {session.model}, температура: {session.temperature}, top_p: {session.top_p}")
        logger.info("Отправляем запрос к LLM сервису")
        
        # Подготавливаем системный промпт с учетом всех настроек
        settings_prompt = f"\n\nНастройки ответа:\n"
        settings_prompt += f"Максимум токенов: {session.max_tokens}\n"
        
        if session.temperature <= 0.3:
            settings_prompt += f"Стиль: Кратко и по делу.\n"
        elif session.temperature <= 0.7:
            settings_prompt += f"Стиль: Умеренно, с примерами.\n"
        else:
            settings_prompt += f"Стиль: Развернуто, с деталями.\n"
            
        if session.top_p <= 0.5:
            settings_prompt += f"Подход: Фактический, проверенная информация.\n"
        else:
            settings_prompt += f"Подход: Креативный, нестандартные идеи.\n"
            
        # Проверяем, есть ли системный промпт
        if not session.system_prompt.strip():
            logger.warning("Системный промпт пустой!")
            system_content = "Ты полезный ассистент. " + context + settings_prompt
        else:
            # Добавляем системный промпт пользователя
            system_content = f"{session.system_prompt}\n\n" + context + settings_prompt
        
        # Проверяем длину системного промпта
        if len(system_content) > 4000:
            logger.warning(f"Системный промпт слишком длинный: {len(system_content)} символов")
            # Обрезаем до 4000 символов
            system_content = system_content[:4000] + "..."
        
        # Логируем системный промпт для отладки
        logger.info(f"Системный промпт пользователя: '{session.system_prompt}'")
        logger.info(f"Контекст из файлов: '{context[:200]}...' (длина: {len(context)})")
        logger.info(f"Настройки модели: '{settings_prompt[:200]}...' (длина: {len(settings_prompt)})")
        logger.info(f"Итоговый системный промпт: '{system_content[:500]}...' (длина: {len(system_content)})")
        logger.info(f"Полный системный промпт: '{system_content}'")
        
        # Функции уже получены из запроса выше
        
        # Проверяем, нужно ли выполнить поиск в интернете
        search_results = ""
        logger.info(f"Проверяем web_search для сессии {session_id}: {session.web_search}")
        if session.web_search:
            logger.info("Включен поиск в интернете, выполняем поиск...")
            llm_service = LLMService()
            search_results_list = llm_service.search_web(user_message, max_results=3)
            search_results = llm_service.format_search_results(search_results_list)
            logger.info(f"Получены результаты поиска: {len(search_results)} символов")
            logger.info(f"Результаты поиска: {search_results[:200]}...")
            
            # Добавляем результаты поиска к системному промпту
            if search_results:
                system_content += f"\n\n{search_results}"
                logger.info("Результаты поиска добавлены к системному промпту")
        else:
            logger.info("Поиск в интернете отключен для этой сессии")
        
        # Отправляем запрос к LLM с файлами и функциями
        logger.info(f"Передаем в LLM сервис модель: '{session.model}'")
        llm_service = LLMService()
        response_data = llm_service.generate_response(
            model=session.model,
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': user_message}
            ],
            temperature=session.temperature,
            top_p=session.top_p,
            max_tokens=session.max_tokens,
            files=training_files,
            functions=functions
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
        
        # Проверяем количество сообщений после сохранения
        final_message_count = session.messages.count()
        logger.info(f"Количество сообщений после сохранения ответа: {final_message_count}")
        
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
        logger.info(f"Загрузка файла для сессии: {session_id}")
        
        if not session_id:
            logger.error("Session ID не предоставлен")
            return JsonResponse({'success': False, 'error': 'Session ID required'})
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            # Создаем новую сессию если она не существует
            session = ChatSession.objects.create(
                session_id=session_id,
                model='GigaChat:latest',  # Значение по умолчанию
                temperature=0.7,
                top_p=1.0,
                max_tokens=4000,
                system_prompt='',
                web_search=False
            )
            logger.info(f"Создана новая сессия для загрузки файла: {session_id}")
        
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file provided'})
        
        file = request.FILES['file']
        
        # Проверяем размер файла (максимум 10MB)
        if file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'File too large. Maximum size is 10MB.'})
        
        # Обрабатываем файл
        processor = FileProcessor()
        file_type, content_preview = processor.process_file(file)
        
        # Проверяем, поддерживается ли тип файла
        if file_type == 'unknown':
            return JsonResponse({'success': False, 'error': 'Unsupported file type'})
        
        # Обрабатываем файл для обучения
        training_data = processor.process_file_for_training(file)
        
        # Сохраняем файл
        uploaded_file = UploadedFile.objects.create(
            session=session,
            file=file,
            filename=file.name,
            file_type=file_type,
            file_size=file.size,
            content_preview=content_preview
        )
        
        logger.info(f"Создан файл: filename='{uploaded_file.filename}', file_type='{uploaded_file.file_type}'")
        logger.info(f"Filename bytes: {uploaded_file.filename.encode('utf-8')}")
        logger.info(f"Filename repr: {repr(uploaded_file.filename)}")
        
        # Подготавливаем ответ с информацией о файле
        response_data = {
            'id': str(uploaded_file.id),
            'filename': uploaded_file.filename,
            'file_type': uploaded_file.file_type,
            'file_size': uploaded_file.file_size,
            'content_preview': uploaded_file.content_preview[:500] + '...' if len(uploaded_file.content_preview) > 500 else uploaded_file.content_preview,
        }
        
        # Добавляем информацию о готовности для обучения
        if 'error' not in training_data:
            response_data['training_ready'] = True
            response_data['training_type'] = training_data.get('type', 'unknown')
            response_data['training_size'] = training_data.get('size', 0)
        else:
            response_data['training_ready'] = False
            response_data['training_error'] = training_data['error']
        
        logger.info(f"Файл успешно загружен: {uploaded_file.filename} для сессии {session_id}")
        logger.info(f"Response data: {response_data}")
        
        return JsonResponse({
            'success': True,
            'file': response_data
        })
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["GET"])
def get_session_files(request, session_id):
    """Получение списка файлов сессии."""
    try:
        session = get_object_or_404(ChatSession, session_id=session_id)
        files = session.files.all()
        
        files_data = []
        processor = FileProcessor()
        
        for file in files:
            # Проверяем готовность файла для обучения
            try:
                training_data = processor.process_file_for_training(file.file)
                training_ready = 'error' not in training_data
                training_type = training_data.get('type', 'unknown') if training_ready else None
                training_size = training_data.get('size', 0) if training_ready else 0
            except Exception as e:
                training_ready = False
                training_type = None
                training_size = 0
            
            files_data.append({
                'id': str(file.id),
                'filename': file.filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'content_preview': file.content_preview[:200] + '...' if len(file.content_preview) > 200 else file.content_preview,
                'uploaded_at': file.uploaded_at.isoformat(),
                'training_ready': training_ready,
                'training_type': training_type,
                'training_size': training_size,
            })
        
        return JsonResponse({
            'success': True,
            'files': files_data,
            'total_files': len(files_data)
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении файлов сессии: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


# Agent views
def agents_list(request):
    """Страница со списком всех агентов."""
    agents = Agent.objects.filter(is_active=True)
    return render(request, 'chat/agents_list.html', {'agents': agents})


def function_manager(request):
    """Страница управления функциями."""
    return render(request, 'chat/function_manager.html')


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
def update_session(request):
    """Обновление настроек сессии."""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        logger.info(f"=== ОБНОВЛЕНИЕ СЕССИИ ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Данные: {data}")
        
        if not session_id:
            return JsonResponse({'success': False, 'error': 'Session ID required'})
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
            logger.info(f"Найдена сессия, текущая модель: {session.model}")
            
            # Проверяем количество сообщений в сессии
            message_count = session.messages.count()
            logger.info(f"Количество сообщений в сессии: {message_count}")
            
        except ChatSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
        
        # Обновляем настройки сессии
        update_fields = []
        
        if 'model' in data:
            session.model = data['model']
            update_fields.append('model')
            
        if 'temperature' in data:
            session.temperature = float(data['temperature'])
            update_fields.append('temperature')
            
        if 'top_p' in data:
            session.top_p = float(data['top_p'])
            update_fields.append('top_p')
            
        if 'max_tokens' in data:
            session.max_tokens = int(data['max_tokens'])
            update_fields.append('max_tokens')
            
        if 'system_prompt' in data:
            session.system_prompt = data['system_prompt']
            update_fields.append('system_prompt')
            
        if 'web_search' in data:
            logger.info(f"Обновляем web_search для сессии {session_id}: {data['web_search']}")
            session.web_search = bool(data['web_search'])
            update_fields.append('web_search')
        
        if update_fields:
            session.save(update_fields=update_fields)
            logger.info(f"Настройки сессии {session_id} обновлены: {', '.join(update_fields)}")
            logger.info(f"Новая модель в сессии: {session.model}")
            
            # Проверяем, что количество сообщений не изменилось
            new_message_count = session.messages.count()
            logger.info(f"Количество сообщений после обновления: {new_message_count}")
            
        else:
            logger.info(f"Нет полей для обновления в сессии {session_id}")
        
        return JsonResponse({'success': True, 'message': 'Сессия обновлена'})
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении сессии: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


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
                'web_search': agent.web_search,
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
                web_search=bool(data.get('web_search', False)),
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
        agent.web_search = bool(data.get('web_search', agent.web_search))
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


# Function management views
@csrf_exempt
@require_http_methods(["GET"])
def get_functions(request):
    """Получение списка всех функций."""
    try:
        functions = PythonFunction.objects.filter(is_active=True)
        functions_data = [func.get_function_info() for func in functions]
        
        return JsonResponse({
            'success': True,
            'functions': functions_data
        })
    except Exception as e:
        logger.error(f"Ошибка при получении функций: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def create_function(request):
    """Создание новой Python функции."""
    try:
        data = json.loads(request.body)
        
        # Валидация данных
        required_fields = ['name', 'description', 'json_definition', 'python_code']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'success': False, 'error': f'Отсутствует поле: {field}'})
        
        # Создаем функцию
        function = PythonFunction.objects.create(
            name=data['name'],
            description=data['description'],
            json_definition=data['json_definition'],
            python_code=data['python_code']
        )
        
        # Валидируем функцию
        is_valid, message = function.validate_function()
        if not is_valid:
            function.delete()
            return JsonResponse({'success': False, 'error': f'Ошибка валидации: {message}'})
        
        return JsonResponse({
            'success': True,
            'function': function.get_function_info()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный JSON формат'})
    except Exception as e:
        logger.error(f"Ошибка при создании функции: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def update_function(request, function_id):
    """Обновление Python функции."""
    try:
        function = get_object_or_404(PythonFunction, id=function_id)
        data = json.loads(request.body)
        
        # Обновляем поля
        if 'name' in data:
            function.name = data['name']
        if 'description' in data:
            function.description = data['description']
        if 'json_definition' in data:
            function.json_definition = data['json_definition']
        if 'python_code' in data:
            function.python_code = data['python_code']
        
        # Валидируем функцию
        is_valid, message = function.validate_function()
        if not is_valid:
            return JsonResponse({'success': False, 'error': f'Ошибка валидации: {message}'})
        
        function.save()
        
        return JsonResponse({
            'success': True,
            'function': function.get_function_info()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный JSON формат'})
    except Exception as e:
        logger.error(f"Ошибка при обновлении функции: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def delete_function(request, function_id):
    """Удаление Python функции."""
    try:
        function = get_object_or_404(PythonFunction, id=function_id)
        
        # Проверяем, используется ли функция в агентах
        agents_using_function = Agent.objects.filter(functions=function)
        if agents_using_function.exists():
            return JsonResponse({
                'success': False, 
                'error': f'Функция используется в {agents_using_function.count()} агентах. Сначала отключите её в агентах.'
            })
        
        function.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Ошибка при удалении функции: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def toggle_agent_function(request, agent_id, function_id):
    """Подключение/отключение функции у агента."""
    try:
        agent = get_object_or_404(Agent, id=agent_id, is_active=True)
        function = get_object_or_404(PythonFunction, id=function_id, is_active=True)
        
        data = json.loads(request.body)
        action = data.get('action', 'toggle')  # 'add', 'remove', 'toggle'
        
        if action == 'add' or (action == 'toggle' and not agent.functions.filter(id=function_id).exists()):
            agent.functions.add(function)
            message = f'Функция "{function.name}" подключена к агенту "{agent.name}"'
        elif action == 'remove' or (action == 'toggle' and agent.functions.filter(id=function_id).exists()):
            agent.functions.remove(function)
            message = f'Функция "{function.name}" отключена от агента "{agent.name}"'
        else:
            message = 'Действие не выполнено'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'agent_functions': [func.get_function_info() for func in agent.functions.filter(is_active=True)]
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный JSON формат'})
    except Exception as e:
        logger.error(f"Ошибка при изменении функций агента: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["GET"])
def get_agent_functions(request, agent_id):
    """Получение функций агента."""
    try:
        agent = get_object_or_404(Agent, id=agent_id, is_active=True)
        functions = agent.functions.filter(is_active=True)
        
        return JsonResponse({
            'success': True,
            'functions': [func.get_function_info() for func in functions]
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении функций агента: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

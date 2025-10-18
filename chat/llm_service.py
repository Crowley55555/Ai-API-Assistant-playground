import os
import requests
import json
import logging
from typing import List, Dict, Any
from .token_counter import TokenCounter

# Настройка логирования
logger = logging.getLogger(__name__)


class LLMService:
    """Сервис для работы с различными LLM API."""
    
    def __init__(self):
        self.gigachat_api_key = os.environ.get('GIGACHAT_API_KEY')
        self.gigachat_client_secret = os.environ.get('GIGACHAT_CLIENT_SECRET')
        self.gigachat_scope = os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
        self.yandex_api_key = os.environ.get('YANDEX_API_KEY')
        self.yandex_folder_id = os.environ.get('YANDEX_FOLDER_ID')
        self.token_counter = TokenCounter()
    
    def generate_response(self, model: str, messages: List[Dict[str, str]], 
                         temperature: float = 0.7, top_p: float = 1.0, max_tokens: int = 4000,
                         files: List[Dict[str, Any]] = None, functions: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Генерирует ответ от LLM и возвращает ответ с информацией о токенах."""
        
        logger.info(f"=== НАЧИНАЕМ ГЕНЕРАЦИЮ ОТВЕТА ===")
        logger.info(f"Модель: '{model}'")
        logger.info(f"Параметры: temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")
        logger.info(f"Количество сообщений: {len(messages)}")
        if files:
            logger.info(f"Количество файлов: {len(files)}")
        if functions:
            logger.info(f"Количество функций: {len(functions)}")
        
        # Обрабатываем файлы и добавляем их к сообщениям
        if files:
            messages = self._process_files_for_messages(messages, files)
        
        # Подсчитываем токены на входе
        input_tokens = self.token_counter.count_messages_tokens(messages, model)
        logger.info(f"Входящие токены: {input_tokens}")
        
        # Определяем провайдера по модели
        logger.info(f"Модель для выбора API: '{model}'")
        
        if 'gigachat' in model.lower():
            logger.info("Используем GigaChat API")
            response_text = self._call_gigachat(model, messages, temperature, top_p, max_tokens, functions)
        elif 'yandex' in model.lower():
            logger.info("Используем Yandex GPT API")
            response_text = self._call_yandex(model, messages, temperature, top_p, max_tokens, functions)
        else:
            # По умолчанию используем GigaChat
            logger.warning(f"Неизвестная модель '{model}', используем GigaChat API (по умолчанию)")
            response_text = self._call_gigachat(model, messages, temperature, top_p, max_tokens, functions)
        
        logger.info(f"Получен ответ длиной: {len(response_text)} символов")
        
        # Подсчитываем токены в ответе
        output_tokens = self.token_counter.count_tokens(response_text, model)
        total_tokens = input_tokens + output_tokens
        
        # Оцениваем стоимость
        cost_info = self.token_counter.estimate_cost(input_tokens, output_tokens, model)
        
        logger.info(f"Итоговые токены: входящие={input_tokens}, исходящие={output_tokens}, всего={total_tokens}")
        logger.info(f"Оценка стоимости: {cost_info}")
        
        return {
            'content': response_text,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'cost': cost_info,
            'model': model
        }
    
    def _process_files_for_messages(self, messages: List[Dict[str, str]], files: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Обрабатывает файлы и добавляет их содержимое к сообщениям."""
        processed_messages = []
        
        for message in messages:
            if message['role'] == 'user' and files:
                # Добавляем содержимое файлов к пользовательскому сообщению
                file_content = self._format_files_content(files)
                if file_content:
                    message_content = message['content']
                    if file_content not in message_content:
                        message_content += f"\n\n{file_content}"
                    
                    processed_messages.append({
                        'role': message['role'],
                        'content': message_content
                    })
                else:
                    processed_messages.append(message)
            else:
                processed_messages.append(message)
        
        return processed_messages
    
    def _format_files_content(self, files: List[Dict[str, Any]]) -> str:
        """Форматирует содержимое файлов для включения в сообщение."""
        if not files:
            return ""
        
        content_parts = []
        
        for file_data in files:
            if 'error' in file_data:
                content_parts.append(f"Ошибка обработки файла: {file_data['error']}")
                continue
            
            file_type = file_data.get('type', 'unknown')
            filename = file_data.get('filename', 'unknown')
            
            if file_type == 'text':
                content_parts.append(f"Содержимое текстового файла '{filename}':\n{file_data['content']}")
            
            elif file_type == 'python':
                content_parts.append(f"Python код из файла '{filename}':\n```python\n{file_data['content']}\n```")
            
            elif file_type == 'pdf':
                content_parts.append(f"Текст из PDF файла '{filename}' ({file_data.get('pages', 0)} страниц):\n{file_data['content']}")
            
            elif file_type == 'json':
                import json
                content_parts.append(f"JSON данные из файла '{filename}':\n```json\n{json.dumps(file_data['content'], ensure_ascii=False, indent=2)}\n```")
            
            elif file_type == 'csv':
                content_parts.append(f"CSV данные из файла '{filename}' ({file_data.get('rows', 0)} строк):\n```csv\n{file_data['content']}\n```")
            
            elif file_type == 'markdown':
                content_parts.append(f"Markdown содержимое из файла '{filename}':\n{file_data['content']}")
            
            elif file_type == 'image':
                # Для изображений добавляем описание
                content_parts.append(f"Изображение '{filename}' ({file_data.get('format', 'unknown')}, {file_data.get('size', 'unknown')} пикселей) - данные в base64 формате готовы для анализа.")
        
        return "\n\n".join(content_parts)
    
    def _call_gigachat(self, model: str, messages: List[Dict[str, str]], 
                      temperature: float, top_p: float, max_tokens: int, functions: List[Dict[str, Any]] = None) -> str:
        """Вызов GigaChat API."""
        if not self.gigachat_api_key:
            logger.error("API ключ GigaChat не настроен")
            return "Ошибка: API ключ GigaChat не настроен"
        
        logger.info(f"API Key (первые 20 символов): {self.gigachat_api_key[:20]}...")
        
        try:
            logger.info("Получаем токен доступа GigaChat")
            
            # Генерируем уникальный RqUID согласно документации
            import uuid
            rq_uid = str(uuid.uuid4())
            logger.info(f"RqUID: {rq_uid}")
            
            # URL для авторизации согласно документации
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            
            # Данные для авторизации согласно документации
            auth_data = {
                "scope": self.gigachat_scope
            }
            
            # Заголовки согласно документации
            auth_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': rq_uid,
                'Authorization': f'Basic {self.gigachat_api_key}'
            }
            
            logger.info(f"URL авторизации: {auth_url}")
            logger.info(f"Данные авторизации: {auth_data}")
            logger.info(f"Заголовки авторизации: {auth_headers}")
            
            # Отправляем запрос согласно документации
            auth_response = requests.post(auth_url, data=auth_data, headers=auth_headers, timeout=30, verify=False)
            logger.info(f"Статус ответа авторизации: {auth_response.status_code}")
            
            if auth_response.status_code != 200:
                logger.error(f"Ошибка авторизации: {auth_response.status_code}")
                logger.error(f"Заголовки ответа: {dict(auth_response.headers)}")
                logger.error(f"Текст ответа: {auth_response.text}")
                return f"Ошибка авторизации GigaChat: {auth_response.status_code} - {auth_response.text}"
            
            auth_result = auth_response.json()
            access_token = auth_result.get('access_token')
            
            if not access_token:
                logger.error("Не удалось получить токен доступа GigaChat")
                return "Ошибка: не удалось получить токен доступа GigaChat"
            
            logger.info("Токен доступа получен, отправляем запрос к GigaChat API")
            # Отправляем запрос к API
            api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            api_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Преобразуем сообщения в формат GigaChat
            gigachat_messages = []
            for msg in messages:
                gigachat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            api_data = {
                "model": model,
                "messages": gigachat_messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens
            }
            
            # Добавляем функции если они есть
            if functions:
                api_data["functions"] = [func.get('json_definition', func) for func in functions]
                api_data["function_call"] = "auto"
            
            logger.info(f"URL: {api_url}")
            logger.info(f"Данные запроса: {json.dumps(api_data, ensure_ascii=False, indent=2)}")
            api_response = requests.post(api_url, headers=api_headers, json=api_data, timeout=30, verify=False)
            logger.info(f"Статус ответа API: {api_response.status_code}")
            api_response.raise_for_status()
            api_result = api_response.json()
            
            logger.info("Успешно получен ответ от GigaChat API")
            response_content = api_result['choices'][0]['message']['content']
            logger.info(f"Ответ GigaChat: {response_content[:200]}...")
            return response_content
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к GigaChat API: {str(e)}")
            return f"Ошибка при обращении к GigaChat API: {str(e)}"
    
    def _call_yandex(self, model: str, messages: List[Dict[str, str]], 
                     temperature: float, top_p: float, max_tokens: int, functions: List[Dict[str, Any]] = None) -> str:
        """Вызов Yandex GPT API."""
        if not self.yandex_api_key:
            logger.error("API ключ Yandex не настроен")
            return "Ошибка: API ключ Yandex не настроен"
        
        if not self.yandex_folder_id:
            logger.error("Folder ID Yandex не настроен")
            return "Ошибка: Folder ID Yandex не настроен"
        
        logger.info("Отправляем запрос к Yandex GPT API")
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {self.yandex_api_key}",
            "Content-Type": "application/json",
            "x-data-logging-enabled": "false"
        }
        
        # Преобразуем сообщения в формат Yandex GPT
        yandex_messages = []
        for msg in messages:
            yandex_messages.append({
                "role": msg["role"],
                "text": msg["content"]
            })
        
        # Определяем правильное имя модели
        if model == 'yandexgpt':
            model_name = 'yandexgpt-lite'
        else:
            model_name = model
            
        # Yandex GPT поддерживает temperature только в диапазоне [0, 1]
        yandex_temperature = min(temperature, 1.0)
        if temperature > 1.0:
            logger.info(f"Yandex GPT: ограничиваем temperature с {temperature} до {yandex_temperature}")
        
        # Yandex GPT поддерживает top_p только в диапазоне [0, 1]
        yandex_top_p = min(top_p, 1.0)
        if top_p > 1.0:
            logger.info(f"Yandex GPT: ограничиваем top_p с {top_p} до {yandex_top_p}")
        
        data = {
            "modelUri": f"gpt://{self.yandex_folder_id}/{model_name}",
            "completionOptions": {
                "stream": False,
                "temperature": yandex_temperature,
                "topP": yandex_top_p,
                "maxTokens": max_tokens
            },
            "messages": yandex_messages
        }
        
        # Используем folder_id (основной идентификатор)
        data["modelUri"] = f"gpt://{self.yandex_folder_id}/{model_name}"
        logger.info(f"Используем folder_id: {self.yandex_folder_id}")
        
        try:
            logger.info(f"URL: {url}")
            logger.info(f"Данные запроса: {json.dumps(data, ensure_ascii=False, indent=2)}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            logger.info(f"Статус ответа: {response.status_code}")
            logger.info(f"Текст ответа: {response.text}")
            response.raise_for_status()
            result = response.json()
            logger.info("Успешно получен ответ от Yandex GPT API")
            response_content = result['result']['alternatives'][0]['message']['text']
            logger.info(f"Ответ Yandex: {response_content[:200]}...")
            return response_content
        except Exception as e:
            logger.error(f"Ошибка при обращении к Yandex GPT API: {str(e)}")
            return f"Ошибка при обращении к Yandex GPT API: {str(e)}"
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Выполняет поиск в интернете по запросу."""
        logger.info(f"Выполняем поиск в интернете: '{query}'")
        
        try:
            # Используем DuckDuckGo API для поиска (бесплатный и не требует API ключа)
            search_url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Обрабатываем основные результаты
            if 'Abstract' in data and data['Abstract']:
                results.append({
                    'title': data.get('Heading', 'Основная информация'),
                    'url': data.get('AbstractURL', ''),
                    'snippet': data['Abstract']
                })
            
            # Обрабатываем связанные темы
            if 'RelatedTopics' in data:
                for topic in data['RelatedTopics'][:max_results-1]:
                    if isinstance(topic, dict) and 'Text' in topic:
                        results.append({
                            'title': topic.get('FirstURL', '').split('/')[-1] if topic.get('FirstURL') else 'Связанная тема',
                            'url': topic.get('FirstURL', ''),
                            'snippet': topic['Text']
                        })
            
            logger.info(f"Найдено результатов поиска: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка при поиске в интернете: {str(e)}")
            return [{
                'title': 'Ошибка поиска',
                'url': '',
                'snippet': f'Не удалось выполнить поиск: {str(e)}'
            }]
    
    def format_search_results(self, results: List[Dict[str, str]]) -> str:
        """Форматирует результаты поиска для включения в контекст."""
        if not results:
            return ""
        
        formatted_results = ["🔍 **Результаты поиска в интернете:**\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Без названия')
            url = result.get('url', '')
            snippet = result.get('snippet', '')
            
            formatted_results.append(f"{i}. **{title}**")
            if url:
                formatted_results.append(f"   URL: {url}")
            if snippet:
                formatted_results.append(f"   {snippet}")
            formatted_results.append("")  # Пустая строка между результатами
        
        return "\n".join(formatted_results)

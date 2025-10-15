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
        self.perplexity_api_key = os.environ.get('PERPLEXITY_API_KEY')
        self.gigachat_api_key = os.environ.get('GIGACHAT_API_KEY')
        self.gigachat_client_secret = os.environ.get('GIGACHAT_CLIENT_SECRET')
        self.gigachat_scope = os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
        self.yandex_api_key = os.environ.get('YANDEX_API_KEY')
        self.yandex_folder_id = os.environ.get('YANDEX_FOLDER_ID')
        self.token_counter = TokenCounter()
    
    def generate_response(self, model: str, messages: List[Dict[str, str]], 
                         temperature: float = 0.7, top_p: float = 1.0, max_tokens: int = 4000) -> Dict[str, Any]:
        """Генерирует ответ от LLM и возвращает ответ с информацией о токенах."""
        
        logger.info(f"Начинаем генерацию ответа для модели: {model}")
        logger.info(f"Параметры: temperature={temperature}, top_p={top_p}, max_tokens={max_tokens}")
        logger.info(f"Количество сообщений: {len(messages)}")
        
        # Подсчитываем токены на входе
        input_tokens = self.token_counter.count_messages_tokens(messages, model)
        logger.info(f"Входящие токены: {input_tokens}")
        
        # Определяем провайдера по модели
        if 'sonar' in model.lower():
            logger.info("Используем Perplexity API")
            response_text = self._call_perplexity(model, messages, temperature, top_p, max_tokens)
        elif 'gigachat' in model.lower():
            logger.info("Используем GigaChat API")
            response_text = self._call_gigachat(model, messages, temperature, top_p, max_tokens)
        elif 'yandex' in model.lower():
            logger.info("Используем Yandex GPT API")
            response_text = self._call_yandex(model, messages, temperature, top_p, max_tokens)
        else:
            # По умолчанию используем Perplexity
            logger.info("Используем Perplexity API (по умолчанию)")
            response_text = self._call_perplexity(model, messages, temperature, top_p, max_tokens)
        
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
    
    
    def _call_perplexity(self, model: str, messages: List[Dict[str, str]], 
                        temperature: float, top_p: float, max_tokens: int) -> str:
        """Вызов Perplexity API."""
        if not self.perplexity_api_key:
            logger.error("API ключ Perplexity не настроен")
            return "Ошибка: API ключ Perplexity не настроен"
        
        logger.info("Отправляем запрос к Perplexity API")
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens
        }
        
        try:
            logger.info(f"URL: {url}")
            logger.info(f"Данные запроса: {json.dumps(data, ensure_ascii=False, indent=2)}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            logger.info(f"Статус ответа: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.info("Успешно получен ответ от Perplexity API")
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Ошибка при обращении к Perplexity API: {str(e)}")
            return f"Ошибка при обращении к Perplexity API: {str(e)}"
    
    def _call_gigachat(self, model: str, messages: List[Dict[str, str]], 
                      temperature: float, top_p: float, max_tokens: int) -> str:
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
            
            logger.info(f"URL: {api_url}")
            logger.info(f"Данные запроса: {json.dumps(api_data, ensure_ascii=False, indent=2)}")
            api_response = requests.post(api_url, headers=api_headers, json=api_data, timeout=30, verify=False)
            logger.info(f"Статус ответа API: {api_response.status_code}")
            api_response.raise_for_status()
            api_result = api_response.json()
            
            logger.info("Успешно получен ответ от GigaChat API")
            return api_result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к GigaChat API: {str(e)}")
            return f"Ошибка при обращении к GigaChat API: {str(e)}"
    
    def _call_yandex(self, model: str, messages: List[Dict[str, str]], 
                     temperature: float, top_p: float, max_tokens: int) -> str:
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
            return result['result']['alternatives'][0]['message']['text']
        except Exception as e:
            logger.error(f"Ошибка при обращении к Yandex GPT API: {str(e)}")
            return f"Ошибка при обращении к Yandex GPT API: {str(e)}"

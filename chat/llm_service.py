import os
import requests
import json
from typing import List, Dict, Any
from .token_counter import TokenCounter


class LLMService:
    """Сервис для работы с различными LLM API."""
    
    def __init__(self):
        self.perplexity_api_key = os.environ.get('PERPLEXITY_API_KEY')
        self.gigachat_api_key = os.environ.get('GIGACHAT_API_KEY')
        self.gigachat_client_secret = os.environ.get('GIGACHAT_CLIENT_SECRET')
        self.gigachat_scope = os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
        self.yandex_api_key = os.environ.get('YANDEX_API_KEY')
        self.token_counter = TokenCounter()
    
    def generate_response(self, model: str, messages: List[Dict[str, str]], 
                         temperature: float = 0.7, top_p: float = 1.0) -> Dict[str, Any]:
        """Генерирует ответ от LLM и возвращает ответ с информацией о токенах."""
        
        # Подсчитываем токены на входе
        input_tokens = self.token_counter.count_messages_tokens(messages, model)
        
        # Определяем провайдера по модели
        if 'sonar' in model.lower():
            response_text = self._call_perplexity(model, messages, temperature, top_p)
        elif 'gigachat' in model.lower():
            response_text = self._call_gigachat(model, messages, temperature, top_p)
        elif 'yandex' in model.lower():
            response_text = self._call_yandex(model, messages, temperature, top_p)
        else:
            # По умолчанию используем Perplexity
            response_text = self._call_perplexity(model, messages, temperature, top_p)
        
        # Подсчитываем токены в ответе
        output_tokens = self.token_counter.count_tokens(response_text, model)
        total_tokens = input_tokens + output_tokens
        
        # Оцениваем стоимость
        cost_info = self.token_counter.estimate_cost(input_tokens, output_tokens, model)
        
        return {
            'content': response_text,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'cost': cost_info,
            'model': model
        }
    
    def _call_perplexity(self, model: str, messages: List[Dict[str, str]], 
                        temperature: float, top_p: float) -> str:
        """Вызов Perplexity API."""
        if not self.perplexity_api_key:
            return "Ошибка: API ключ Perplexity не настроен"
        
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
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Ошибка при обращении к Perplexity API: {str(e)}"
    
    def _call_gigachat(self, model: str, messages: List[Dict[str, str]], 
                      temperature: float, top_p: float) -> str:
        """Вызов GigaChat API."""
        if not self.gigachat_api_key or not self.gigachat_client_secret:
            return "Ошибка: API ключ или client secret GigaChat не настроен"
        
        try:
            # Получаем токен доступа
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            auth_data = {
                "scope": self.gigachat_scope
            }
            auth_headers = {
                "Authorization": f"Bearer {self.gigachat_api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            auth_response = requests.post(auth_url, data=auth_data, headers=auth_headers, timeout=30)
            auth_response.raise_for_status()
            auth_result = auth_response.json()
            access_token = auth_result.get('access_token')
            
            if not access_token:
                return "Ошибка: не удалось получить токен доступа GigaChat"
            
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
                "max_tokens": 4000
            }
            
            api_response = requests.post(api_url, headers=api_headers, json=api_data, timeout=30)
            api_response.raise_for_status()
            api_result = api_response.json()
            
            return api_result['choices'][0]['message']['content']
            
        except Exception as e:
            return f"Ошибка при обращении к GigaChat API: {str(e)}"
    
    def _call_yandex(self, model: str, messages: List[Dict[str, str]], 
                    temperature: float, top_p: float) -> str:
        """Вызов Yandex GPT API."""
        if not self.yandex_api_key:
            return "Ошибка: API ключ Yandex не настроен"
        
        # Здесь должна быть реализация для Yandex GPT API
        # Пока возвращаем заглушку
        return "Yandex GPT API пока не реализован"

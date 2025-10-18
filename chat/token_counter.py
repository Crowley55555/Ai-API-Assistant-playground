import tiktoken
import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class TokenCounter:
    """Сервис для подсчета токенов в тексте."""
    
    def __init__(self):
        # Кодировки для разных моделей
        self.encodings = {
            'gpt-4': tiktoken.encoding_for_model('gpt-4'),
            'gpt-3.5-turbo': tiktoken.encoding_for_model('gpt-3.5-turbo'),
            'llama-3.1-sonar-small-128k-online': tiktoken.encoding_for_model('gpt-4'),  # Используем GPT-4 как приближение
            'llama-3.1-sonar-large-128k-online': tiktoken.encoding_for_model('gpt-4'),
            'llama-3.1-sonar-huge-128k-online': tiktoken.encoding_for_model('gpt-4'),
            'GigaChat:latest': tiktoken.encoding_for_model('gpt-4'),
            'GigaChat-Pro:latest': tiktoken.encoding_for_model('gpt-4'),
            'yandexgpt': tiktoken.encoding_for_model('gpt-4'),
            'yandexgpt-lite': tiktoken.encoding_for_model('gpt-4'),
        }
    
    def count_tokens(self, text: str, model: str = 'gpt-4') -> int:
        """Подсчитывает количество токенов в тексте для указанной модели."""
        try:
            # Специальная обработка для Yandex GPT - более точный подсчет
            if 'yandex' in model.lower():
                # Для Yandex GPT используем более точный подсчет
                # Примерно 1 токен = 4-5 символов для русского текста
                # Учитываем, что русские слова короче английских
                token_count = len(text) // 4.5
                logger.info(f"Подсчет токенов для Yandex модели '{model}': {int(token_count)} токенов для текста длиной {len(text)} символов")
                return int(token_count)
            
            # Специальная обработка для GigaChat - более точный подсчет
            if 'gigachat' in model.lower():
                # Для GigaChat используем более точный подсчет
                # Примерно 1 токен = 4-5 символов для русского текста
                token_count = len(text) // 4.5
                logger.info(f"Подсчет токенов для GigaChat модели '{model}': {int(token_count)} токенов для текста длиной {len(text)} символов")
                return int(token_count)
            
            encoding = self.encodings.get(model, self.encodings['gpt-4'])
            token_count = len(encoding.encode(text))
            logger.info(f"Подсчет токенов для модели '{model}': {token_count} токенов для текста длиной {len(text)} символов")
            return token_count
        except Exception as e:
            # Fallback: приблизительный подсчет (1 токен ≈ 4 символа)
            fallback_count = len(text) // 4
            logger.warning(f"Ошибка подсчета токенов для модели '{model}': {e}. Используем приблизительный подсчет: {fallback_count}")
            return fallback_count
    
    def count_messages_tokens(self, messages: List[Dict[str, str]], model: str = 'gpt-4') -> int:
        """Подсчитывает общее количество токенов в списке сообщений."""
        total_tokens = 0
        
        for i, message in enumerate(messages):
            role = message.get('role', '')
            content = message.get('content', '')
            
            # Считаем токены для роли и контента
            role_tokens = self.count_tokens(role, model)
            content_tokens = self.count_tokens(content, model)
            
            # Для каждого сообщения добавляем токены форматирования (примерно 3-4 токена)
            message_tokens = role_tokens + content_tokens + 3
            total_tokens += message_tokens
            
            logger.info(f"Сообщение {i+1}: роль='{role}' ({role_tokens} токенов), контент={len(content)} символов ({content_tokens} токенов), всего для сообщения: {message_tokens}")
        
        # Добавляем токены для начала и конца разговора (примерно 2-3 токена)
        total_tokens += 2
        
        logger.info(f"Общее количество токенов для {len(messages)} сообщений: {total_tokens}")
        return total_tokens
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> Dict[str, float]:
        """Оценивает стоимость запроса на основе количества токенов."""
        # Примерные цены за 1000 токенов (в долларах)
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002},
            'llama-3.1-sonar-small-128k-online': {'input': 0.0002, 'output': 0.0002},
            'llama-3.1-sonar-large-128k-online': {'input': 0.0005, 'output': 0.0005},
            'llama-3.1-sonar-huge-128k-online': {'input': 0.001, 'output': 0.001},
            'GigaChat:latest': {'input': 0.0001, 'output': 0.0001},
            'GigaChat-Pro:latest': {'input': 0.0002, 'output': 0.0002},
            'yandexgpt': {'input': 0.0001, 'output': 0.0001},
            'yandexgpt-lite': {'input': 0.00005, 'output': 0.00005},
        }
        
        model_pricing = pricing.get(model, pricing['gpt-4'])
        
        input_cost = (input_tokens / 1000) * model_pricing['input']
        output_cost = (output_tokens / 1000) * model_pricing['output']
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost,
            'input_price_per_1k': model_pricing['input'],
            'output_price_per_1k': model_pricing['output']
        }
    
    def get_token_stats(self, input_messages: List[Dict[str, str]], 
                       output_text: str, model: str) -> Dict:
        """Получает полную статистику токенов для запроса."""
        input_tokens = self.count_messages_tokens(input_messages, model)
        output_tokens = self.count_tokens(output_text, model)
        total_tokens = input_tokens + output_tokens
        
        cost_info = self.estimate_cost(input_tokens, output_tokens, model)
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'model': model,
            'cost': cost_info,
            'timestamp': None  # Будет установлено в view
        }

import tiktoken
import re
from typing import Dict, List, Tuple


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
            encoding = self.encodings.get(model, self.encodings['gpt-4'])
            return len(encoding.encode(text))
        except Exception as e:
            # Fallback: приблизительный подсчет (1 токен ≈ 4 символа)
            return len(text) // 4
    
    def count_messages_tokens(self, messages: List[Dict[str, str]], model: str = 'gpt-4') -> int:
        """Подсчитывает общее количество токенов в списке сообщений."""
        total_tokens = 0
        
        for message in messages:
            # Токены для роли
            total_tokens += self.count_tokens(message.get('role', ''), model)
            # Токены для содержимого
            total_tokens += self.count_tokens(message.get('content', ''), model)
            # Дополнительные токены для форматирования (приблизительно)
            total_tokens += 4
        
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

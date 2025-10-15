#!/usr/bin/env python3
"""
Детальный тест для GigaChat API с разными параметрами
"""

import os
import sys
import django
import requests
import base64
from requests.auth import HTTPBasicAuth

# Настройка Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_playground.settings')
django.setup()

def test_gigachat_detailed():
    """Детальный тест GigaChat API с разными параметрами"""
    
    print("Детальный тест GigaChat API...")
    
    # Загружаем переменные из .env
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get('GIGACHAT_API_KEY')
    client_secret = os.environ.get('GIGACHAT_CLIENT_SECRET')
    scope = os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
    
    if not api_key or not client_secret:
        print("Не все переменные окружения настроены!")
        return False
    
    # Декодируем API key
    try:
        decoded_key = base64.b64decode(api_key).decode('utf-8')
        client_id, client_secret_decoded = decoded_key.split(':')
        print(f"Client ID: {client_id}")
        print(f"Client Secret: {client_secret_decoded}")
    except Exception as e:
        print(f"Ошибка декодирования API key: {e}")
        return False
    
    # Основной URL
    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    # Разные варианты данных для тестирования
    test_cases = [
        # Базовые варианты
        {"name": "Только scope", "data": {"scope": scope}},
        {"name": "Scope + grant_type", "data": {"scope": scope, "grant_type": "client_credentials"}},
        {"name": "Scope + grant_type + client_id", "data": {"scope": scope, "grant_type": "client_credentials", "client_id": client_id}},
        
        # Варианты с разными grant_type
        {"name": "Grant type authorization_code", "data": {"scope": scope, "grant_type": "authorization_code"}},
        {"name": "Grant type password", "data": {"scope": scope, "grant_type": "password"}},
        {"name": "Grant type refresh_token", "data": {"scope": scope, "grant_type": "refresh_token"}},
        
        # Варианты с дополнительными параметрами
        {"name": "С response_type", "data": {"scope": scope, "response_type": "code"}},
        {"name": "С redirect_uri", "data": {"scope": scope, "redirect_uri": "http://localhost:8000"}},
        {"name": "С state", "data": {"scope": scope, "state": "test_state"}},
        
        # Комбинированные варианты
        {"name": "Полный набор", "data": {
            "scope": scope, 
            "grant_type": "client_credentials",
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost:8000"
        }},
        
        # Варианты с разными scope
        {"name": "Scope CORP", "data": {"scope": "GIGACHAT_API_CORP"}},
        {"name": "Без scope", "data": {"grant_type": "client_credentials"}},
        {"name": "Пустые данные", "data": {}},
    ]
    
    print(f"\nТестируем {len(test_cases)} вариантов данных...")
    
    for i, test_case in enumerate(test_cases):
        print(f"\n--- Тест {i+1}: {test_case['name']} ---")
        print(f"Данные: {test_case['data']}")
        
        try:
            auth = HTTPBasicAuth(client_id, client_secret_decoded)
            response = requests.post(auth_url, data=test_case['data'], auth=auth, timeout=30, verify=False)
            
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                print(f"УСПЕХ! Токен получен: {access_token[:20]}...")
                return True
            elif response.status_code == 400:
                print(f"400 Bad Request: {response.text[:200]}...")
            elif response.status_code == 401:
                print(f"401 Unauthorized: {response.text[:200]}...")
            elif response.status_code == 403:
                print(f"403 Forbidden: {response.text[:200]}...")
            else:
                print(f"Другой статус: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Ошибка: {e}")
    
    print("\nВсе варианты не сработали!")
    return False

if __name__ == "__main__":
    print("Запускаем детальный тест GigaChat API...")
    
    success = test_gigachat_detailed()
    
    if success:
        print("\nТест прошел успешно!")
    else:
        print("\nТест не прошел!")
    
    print("\nТест завершен!")

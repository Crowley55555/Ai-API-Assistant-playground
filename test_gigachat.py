#!/usr/bin/env python3
"""
Простой тест для проверки обращения к GigaChat API
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

def test_gigachat_auth():
    """Тестируем авторизацию в GigaChat API"""
    
    print("Тестируем GigaChat API...")
    
    # Загружаем переменные из .env
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get('GIGACHAT_API_KEY')
    client_secret = os.environ.get('GIGACHAT_CLIENT_SECRET')
    scope = os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
    
    print(f"API Key: {api_key[:20]}..." if api_key else "API Key не найден")
    print(f"Client Secret: {client_secret[:20]}..." if client_secret else "Client Secret не найден")
    print(f"Scope: {scope}")
    
    if not api_key or not client_secret:
        print("Не все переменные окружения настроены!")
        return False
    
    # URL для авторизации - попробуем разные варианты
    auth_urls = [
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/token",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/authorize",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/access_token",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/authorize/token"
    ]
    
    # Данные для запроса - попробуем разные форматы
    auth_data_form = {
        "scope": scope
    }
    
    auth_data_json = {
        "scope": scope,
        "grant_type": "client_credentials"
    }
    
    print(f"\nТестируем {len(auth_urls)} URL для авторизации...")
    print(f"Данные form: {auth_data_form}")
    print(f"Данные json: {auth_data_json}")
    
    # Декодируем API key один раз
    try:
        decoded_key = base64.b64decode(api_key).decode('utf-8')
        client_id, client_secret_decoded = decoded_key.split(':')
        print(f"Client ID: {client_id}")
        print(f"Client Secret: {client_secret_decoded}")
    except Exception as e:
        print(f"Ошибка декодирования API key: {e}")
        return False
    
    # Тестируем все комбинации URL + форматов данных
    for i, auth_url in enumerate(auth_urls):
        print(f"\n--- Тестируем URL {i+1}: {auth_url} ---")
        
        # Вариант A: form data
        try:
            print("Вариант A: form data...")
            auth = HTTPBasicAuth(client_id, client_secret_decoded)
            response = requests.post(auth_url, data=auth_data_form, auth=auth, timeout=30, verify=False)
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                print(f"УСПЕХ! Токен получен: {access_token[:20]}...")
                return True
            else:
                print(f"Ошибка: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Вариант A не сработал: {e}")
        
        # Вариант B: JSON data
        try:
            print("Вариант B: JSON data...")
            auth = HTTPBasicAuth(client_id, client_secret_decoded)
            headers = {'Content-Type': 'application/json'}
            response = requests.post(auth_url, json=auth_data_json, auth=auth, headers=headers, timeout=30, verify=False)
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                print(f"УСПЕХ! Токен получен: {access_token[:20]}...")
                return True
            else:
                print(f"Ошибка: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Вариант B не сработал: {e}")
        
        # Вариант C: без grant_type
        try:
            print("Вариант C: JSON без grant_type...")
            auth = HTTPBasicAuth(client_id, client_secret_decoded)
            headers = {'Content-Type': 'application/json'}
            simple_data = {"scope": scope}
            response = requests.post(auth_url, json=simple_data, auth=auth, headers=headers, timeout=30, verify=False)
            print(f"Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                print(f"УСПЕХ! Токен получен: {access_token[:20]}...")
                return True
            else:
                print(f"Ошибка: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Вариант C не сработал: {e}")
    
    # Вариант 2: Используем client_secret из .env
    try:
        print("\nВариант 2: Используем client_secret из .env...")
        auth = HTTPBasicAuth(api_key, client_secret)
        
        response = requests.post(auth_url, data=auth_data, auth=auth, timeout=30, verify=False)
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            print(f"Токен получен: {access_token[:20]}...")
            return True
        else:
            print(f"Ошибка: {response.text}")
            
    except Exception as e:
        print(f"Вариант 2 не сработал: {e}")
    
    # Вариант 3: Пробуем альтернативные URL
    alt_urls = [
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/token",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/authorize",
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth/access_token"
    ]
    
    for i, alt_url in enumerate(alt_urls, 3):
        try:
            print(f"\nВариант {i}: Пробуем URL {alt_url}...")
            
            # Пробуем с декодированным API key
            try:
                decoded_key = base64.b64decode(api_key).decode('utf-8')
                client_id, client_secret_decoded = decoded_key.split(':')
                auth = HTTPBasicAuth(client_id, client_secret_decoded)
            except:
                auth = HTTPBasicAuth(api_key, client_secret)
            
            response = requests.post(alt_url, data=auth_data, auth=auth, timeout=30, verify=False)
            print(f"Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                print(f"Токен получен: {access_token[:20]}...")
                return True
            else:
                print(f"Ошибка: {response.text}")
                
        except Exception as e:
            print(f"Вариант {i} не сработал: {e}")
    
    print("\nВсе варианты не сработали!")
    return False

def test_gigachat_chat():
    """Тестируем отправку сообщения в GigaChat"""
    
    print("\nТестируем отправку сообщения в GigaChat...")
    
    # Сначала получаем токен
    if not test_gigachat_auth():
        print("Не удалось получить токен для тестирования чата")
        return False
    
    # Здесь можно добавить тест отправки сообщения
    print("Токен получен, можно тестировать чат")
    return True

if __name__ == "__main__":
    print("Запускаем тест GigaChat API...")
    
    # Тестируем авторизацию
    success = test_gigachat_auth()
    
    if success:
        print("\nТест авторизации прошел успешно!")
        # Тестируем чат
        test_gigachat_chat()
    else:
        print("\nТест авторизации не прошел!")
    
    print("\nТест завершен!")

#!/usr/bin/env python3
"""
Тест GigaChat API согласно официальной документации
"""

import os
import sys
import django
import requests
import uuid

# Настройка Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_playground.settings')
django.setup()

def test_gigachat_official():
    """Тест GigaChat API согласно официальной документации"""
    
    print("Тест GigaChat API согласно официальной документации...")
    
    # Загружаем переменные из .env
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get('GIGACHAT_API_KEY')
    scope = os.environ.get('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
    
    if not api_key:
        print("API ключ GigaChat не найден!")
        return False
    
    print(f"API Key: {api_key[:20]}...")
    print(f"Scope: {scope}")
    
    # Генерируем уникальный RqUID согласно документации
    rq_uid = str(uuid.uuid4())
    print(f"RqUID: {rq_uid}")
    
    # URL для авторизации согласно документации
    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    # Данные для авторизации согласно документации
    auth_data = {
        "scope": scope
    }
    
    # Заголовки согласно документации
    auth_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': rq_uid,
        'Authorization': f'Basic {api_key}'
    }
    
    print(f"\nURL авторизации: {auth_url}")
    print(f"Данные авторизации: {auth_data}")
    print(f"Заголовки авторизации: {auth_headers}")
    
    try:
        # Отправляем запрос согласно документации
        print("\nОтправляем запрос на получение токена...")
        auth_response = requests.post(auth_url, data=auth_data, headers=auth_headers, timeout=30, verify=False)
        
        print(f"Статус ответа: {auth_response.status_code}")
        print(f"Заголовки ответа: {dict(auth_response.headers)}")
        print(f"Текст ответа: {auth_response.text}")
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            access_token = auth_result.get('access_token')
            expires_at = auth_result.get('expires_at')
            
            print(f"\nУСПЕХ! Токен получен:")
            print(f"Access Token: {access_token[:50]}...")
            print(f"Expires At: {expires_at}")
            
            # Теперь попробуем отправить сообщение
            print("\nТестируем отправку сообщения...")
            
            # URL для отправки сообщения
            chat_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            
            # Данные для отправки сообщения
            chat_data = {
                "model": "GigaChat",
                "messages": [
                    {
                        "role": "user",
                        "content": "Привет! Расскажи о себе в двух словах."
                    }
                ],
                "stream": False,
                "update_interval": 0
            }
            
            # Заголовки для отправки сообщения
            chat_headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            print(f"URL чата: {chat_url}")
            print(f"Данные чата: {chat_data}")
            print(f"Заголовки чата: {chat_headers}")
            
            chat_response = requests.post(chat_url, json=chat_data, headers=chat_headers, timeout=30, verify=False)
            
            print(f"\nСтатус ответа чата: {chat_response.status_code}")
            print(f"Заголовки ответа чата: {dict(chat_response.headers)}")
            print(f"Текст ответа чата: {chat_response.text}")
            
            if chat_response.status_code == 200:
                chat_result = chat_response.json()
                print(f"\nУСПЕХ! Ответ получен:")
                print(f"Ответ: {chat_result}")
                return True
            else:
                print(f"\nОшибка отправки сообщения: {chat_response.status_code}")
                return False
                
        else:
            print(f"\nОшибка получения токена: {auth_response.status_code}")
            return False
            
    except Exception as e:
        print(f"\nОшибка: {e}")
        return False

if __name__ == "__main__":
    print("Запускаем тест GigaChat API согласно официальной документации...")
    
    success = test_gigachat_official()
    
    if success:
        print("\nТест прошел успешно!")
    else:
        print("\nТест не прошел!")
    
    print("\nТест завершен!")

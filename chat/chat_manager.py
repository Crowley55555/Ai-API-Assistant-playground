"""
Менеджер чатов для единообразной работы с разными чатами.
Реализует принципы SOLID и DRY.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ChatSettings:
    """Настройки чата."""
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    system_prompt: str
    web_search: bool
    functions: List[Dict[str, Any]]


@dataclass
class ChatMessage:
    """Сообщение в чате."""
    id: str
    role: str
    content: str
    timestamp: str
    token_stats: Optional[Dict[str, Any]] = None


@dataclass
class ChatSession:
    """Сессия чата."""
    session_id: str
    settings: ChatSettings
    messages: List[ChatMessage]
    stats: Optional[Dict[str, Any]] = None


class ChatAPI(ABC):
    """Абстрактный класс для работы с API чатов."""
    
    @abstractmethod
    async def create_session(self, settings: ChatSettings) -> str:
        """Создает новую сессию чата."""
        pass
    
    @abstractmethod
    async def send_message(self, session_id: str, message: str, functions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Отправляет сообщение в чат."""
        pass
    
    @abstractmethod
    async def update_session_settings(self, session_id: str, settings: ChatSettings) -> bool:
        """Обновляет настройки сессии."""
        pass


class DjangoChatAPI(ChatAPI):
    """Реализация API для Django backend."""
    
    def __init__(self, csrf_token: str):
        self.csrf_token = csrf_token
        self.base_url = '/playground/api'
    
    async def create_session(self, settings: ChatSettings) -> str:
        """Создает новую сессию чата."""
        import requests
        
        response = requests.post(
            f'{self.base_url}/create-session/',
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token
            },
            json={
                'model': settings.model,
                'temperature': settings.temperature,
                'top_p': settings.top_p,
                'max_tokens': settings.max_tokens,
                'system_prompt': settings.system_prompt,
                'web_search': settings.web_search,
                'functions': settings.functions
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['session_id']
        
        raise Exception(f"Failed to create session: {response.text}")
    
    async def send_message(self, session_id: str, message: str, functions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Отправляет сообщение в чат."""
        import requests
        
        response = requests.post(
            f'{self.base_url}/send-message/',
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token
            },
            json={
                'session_id': session_id,
                'message': message,
                'functions': functions
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data
        
        raise Exception(f"Failed to send message: {response.text}")
    
    async def update_session_settings(self, session_id: str, settings: ChatSettings) -> bool:
        """Обновляет настройки сессии."""
        import requests
        
        response = requests.post(
            f'{self.base_url}/update-session/',
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token
            },
            json={
                'session_id': session_id,
                'model': settings.model,
                'temperature': settings.temperature,
                'top_p': settings.top_p,
                'max_tokens': settings.max_tokens,
                'system_prompt': settings.system_prompt,
                'web_search': settings.web_search
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('success', False)
        
        return False


class ChatManager:
    """Менеджер для управления чатами."""
    
    def __init__(self, api: ChatAPI):
        self.api = api
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_chat_session(self, chat_id: str, settings: ChatSettings) -> ChatSession:
        """Создает новую сессию чата."""
        session = ChatSession(
            session_id="",
            settings=settings,
            messages=[]
        )
        self.sessions[chat_id] = session
        return session
    
    async def initialize_session(self, chat_id: str) -> str:
        """Инициализирует сессию чата."""
        if chat_id not in self.sessions:
            raise Exception(f"Chat session {chat_id} not found")
        
        session = self.sessions[chat_id]
        session_id = await self.api.create_session(session.settings)
        session.session_id = session_id
        
        logger.info(f"Session initialized for chat {chat_id}: {session_id}")
        return session_id
    
    async def send_message(self, chat_id: str, message: str) -> ChatMessage:
        """Отправляет сообщение в чат."""
        if chat_id not in self.sessions:
            raise Exception(f"Chat session {chat_id} not found")
        
        session = self.sessions[chat_id]
        
        # Если нет session_id, инициализируем сессию
        if not session.session_id:
            await self.initialize_session(chat_id)
        
        # Добавляем сообщение пользователя
        user_message = ChatMessage(
            id=str(len(session.messages) + 1),
            role='user',
            content=message,
            timestamp=self._get_timestamp()
        )
        session.messages.append(user_message)
        
        # Отправляем сообщение через API
        response = await self.api.send_message(
            session.session_id,
            message,
            session.settings.functions
        )
        
        # Добавляем ответ ассистента
        assistant_message = ChatMessage(
            id=str(len(session.messages) + 1),
            role='assistant',
            content=response['assistant_message']['content'],
            timestamp=response['assistant_message']['timestamp'],
            token_stats=response['assistant_message']['token_stats']
        )
        session.messages.append(assistant_message)
        
        # Обновляем статистику
        if 'session_stats' in response:
            session.stats = response['session_stats']
        
        logger.info(f"Message sent to chat {chat_id}, response length: {len(assistant_message.content)}")
        return assistant_message
    
    async def update_settings(self, chat_id: str, settings: ChatSettings) -> bool:
        """Обновляет настройки чата."""
        if chat_id not in self.sessions:
            raise Exception(f"Chat session {chat_id} not found")
        
        session = self.sessions[chat_id]
        session.settings = settings
        
        # Если есть session_id, обновляем настройки на сервере
        if session.session_id:
            success = await self.api.update_session_settings(session.session_id, settings)
            if success:
                logger.info(f"Settings updated for chat {chat_id}")
            return success
        
        return True
    
    def get_session(self, chat_id: str) -> Optional[ChatSession]:
        """Получает сессию чата."""
        return self.sessions.get(chat_id)
    
    def clear_messages(self, chat_id: str):
        """Очищает сообщения чата."""
        if chat_id in self.sessions:
            self.sessions[chat_id].messages = []
            logger.info(f"Messages cleared for chat {chat_id}")
    
    def _get_timestamp(self) -> str:
        """Получает текущий timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


class ChatFactory:
    """Фабрика для создания чатов."""
    
    @staticmethod
    def create_chat_manager(csrf_token: str) -> ChatManager:
        """Создает менеджер чатов."""
        api = DjangoChatAPI(csrf_token)
        return ChatManager(api)
    
    @staticmethod
    def create_settings(
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        system_prompt: str = "",
        web_search: bool = False,
        functions: List[Dict[str, Any]] = None
    ) -> ChatSettings:
        """Создает настройки чата."""
        if functions is None:
            functions = []
        
        return ChatSettings(
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            web_search=web_search,
            functions=functions
        )

from django.db import models
from django.utils import timezone
import uuid
import json


class ChatSession(models.Model):
    """Модель для хранения сессий чата."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=100)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(default=1.0)
    max_tokens = models.PositiveIntegerField(default=4000)
    system_prompt = models.TextField(blank=True)
    python_functions = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Статистика токенов по сессии
    total_input_tokens = models.PositiveIntegerField(default=0, help_text="Общее количество входных токенов")
    total_output_tokens = models.PositiveIntegerField(default=0, help_text="Общее количество выходных токенов")
    total_tokens = models.PositiveIntegerField(default=0, help_text="Общее количество токенов")
    total_estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0, help_text="Общая примерная стоимость")
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title or 'Безымянная сессия'} ({self.model})"
    
    def update_token_stats(self):
        """Обновляет статистику токенов на основе всех сообщений в сессии."""
        messages = self.messages.all()
        
        self.total_input_tokens = sum(msg.input_tokens for msg in messages)
        self.total_output_tokens = sum(msg.output_tokens for msg in messages)
        self.total_tokens = sum(msg.total_tokens for msg in messages)
        self.total_estimated_cost = sum(msg.estimated_cost for msg in messages)
        
        self.save(update_fields=['total_input_tokens', 'total_output_tokens', 
                               'total_tokens', 'total_estimated_cost'])
    
    def get_token_stats(self):
        """Возвращает статистику токенов для сессии."""
        return {
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_tokens,
            'total_estimated_cost': float(self.total_estimated_cost),
            'message_count': self.messages.count(),
        }


class Message(models.Model):
    """Модель для хранения сообщений в чате."""
    ROLE_CHOICES = [
        ('user', 'Пользователь'),
        ('assistant', 'Ассистент'),
        ('system', 'Система'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Поля для токенизации
    input_tokens = models.PositiveIntegerField(default=0, help_text="Количество токенов на входе")
    output_tokens = models.PositiveIntegerField(default=0, help_text="Количество токенов в ответе")
    total_tokens = models.PositiveIntegerField(default=0, help_text="Общее количество токенов")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0, help_text="Примерная стоимость в долларах")
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class UploadedFile(models.Model):
    """Модель для хранения загруженных файлов."""
    FILE_TYPE_CHOICES = [
        ('text', 'Текстовый файл'),
        ('pdf', 'PDF документ'),
        ('image', 'Изображение'),
        ('python', 'Python скрипт'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    file_size = models.PositiveIntegerField()
    content_preview = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.filename} ({self.file_type})"


class Agent(models.Model):
    """Модель для хранения агентов с их настройками."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Название агента")
    description = models.TextField(blank=True, help_text="Описание агента")
    
    # Настройки модели
    model = models.CharField(max_length=100, help_text="Модель ИИ")
    temperature = models.FloatField(default=0.7, help_text="Температура")
    top_p = models.FloatField(default=1.0, help_text="Top P")
    max_tokens = models.PositiveIntegerField(default=4000, help_text="Максимальное количество токенов")
    system_prompt = models.TextField(blank=True, help_text="Системный промпт")
    
    # Метаданные
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Активен ли агент")
    
    # Связь с сессиями
    current_session = models.ForeignKey(
        ChatSession, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='agent_sessions',
        help_text="Текущая активная сессия агента"
    )
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.model})"
    
    def create_new_session(self):
        """Создает новую сессию для агента."""
        session = ChatSession.objects.create(
            session_id=str(uuid.uuid4()),
            title=f"Сессия {self.name}",
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            system_prompt=self.system_prompt,
        )
        self.current_session = session
        self.save()
        return session
    
    def get_or_create_session(self):
        """Получает текущую сессию или создает новую."""
        if not self.current_session:
            return self.create_new_session()
        return self.current_session
    
    def get_settings(self):
        """Возвращает настройки агента в виде словаря."""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'max_tokens': self.max_tokens,
            'system_prompt': self.system_prompt,
        }
    
    def update_settings(self, **kwargs):
        """Обновляет настройки агента."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()
    
    def get_sessions(self):
        """Возвращает все сессии агента."""
        return ChatSession.objects.filter(
            model=self.model,
            system_prompt=self.system_prompt
        ).order_by('-created_at')
    
    def get_total_stats(self):
        """Возвращает общую статистику по всем сессиям агента."""
        sessions = self.get_sessions()
        return {
            'total_sessions': sessions.count(),
            'total_messages': sum(s.messages.count() for s in sessions),
            'total_tokens': sum(s.total_tokens for s in sessions),
            'total_cost': sum(float(s.total_estimated_cost) for s in sessions),
        }

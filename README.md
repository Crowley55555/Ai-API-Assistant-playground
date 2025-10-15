# AI Playground

Полнофункциональное Django-приложение, имитирующее интерфейс OpenAI Playground с расширенными возможностями.

## Возможности

- 🚀 **Множество моделей ИИ**: Поддержка Perplexity, GigaChat, Yandex GPT
- 📁 **Загрузка файлов**: PDF, изображения, Python скрипты, текстовые файлы
- 🔄 **Сравнение моделей**: Параллельное тестирование с независимыми настройками
- 📚 **История чатов**: Сохранение и управление сессиями
- 🎨 **Современный UI**: Адаптивный дизайн с темной/светлой темой
- ⚡ **Динамические обновления**: HTMX и Alpine.js для интерактивности
- 📊 **Подсчет токенов**: Отслеживание затрат токенов и стоимости запросов
- 🤖 **Система агентов**: Создание и управление персональными агентами с сохраненными настройками
- 💰 **Аналитика расходов**: Детальная статистика по использованию API

## Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd ai-playground
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Настройте базу данных:**
   
   **Вариант 1: SQLite (рекомендуется для разработки)**
   ```bash
   # Ничего дополнительно настраивать не нужно
   # SQLite будет использоваться по умолчанию
   ```
   
   **Вариант 2: PostgreSQL (для продакшена)**
   ```bash
   # Создайте базу данных
   createdb ai_playground
   # Установите переменную окружения
   export USE_POSTGRESQL=True
   ```

5. **Скопируйте файл окружения:**
```bash
cp env.example .env
```

6. **Настройте переменные окружения в `.env`:**
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
# Для PostgreSQL раскомментируйте и настройте:
# USE_POSTGRESQL=True
# DB_NAME=ai_playground
# DB_USER=postgres
# DB_PASSWORD=your-password

# LLM API Keys
PERPLEXITY_API_KEY=your-perplexity-api-key
GIGACHAT_API_KEY=your-gigachat-api-key
GIGACHAT_CLIENT_SECRET=your-gigachat-client-secret
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# Yandex GPT API Settings
YANDEX_API_KEY=your-yandex-api-key
YANDEX_FOLDER_ID=your-folder-id

# Default LLM Provider
DEFAULT_LLM_PROVIDER=gigachat
```

7. **Выполните миграции:**
```bash
python manage.py makemigrations
python manage.py migrate
```

8. **Создайте суперпользователя (опционально):**
```bash
python manage.py createsuperuser
```

9. **Запустите сервер:**
```bash
python manage.py runserver
```

## Структура проекта

```
ai_playground/
├── ai_playground/          # Основные настройки Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                   # Главная страница
│   ├── views.py
│   └── urls.py
├── chat/                   # Основная логика чата и агентов
│   ├── models.py          # Модели для сессий, сообщений и агентов
│   ├── views.py           # Views для playground, истории и агентов
│   ├── llm_service.py     # Интеграция с LLM API
│   ├── token_counter.py   # Подсчет токенов и стоимости
│   ├── model_config.py    # Конфигурация доступных моделей
│   ├── file_processor.py  # Обработка загруженных файлов
│   └── templatetags/      # Template tags для моделей
├── api/                    # API endpoints
├── templates/              # HTML шаблоны
│   ├── base.html
│   ├── core/
│   │   └── welcome.html
│   └── chat/
│       ├── playground.html
│       ├── history.html
│       ├── token_stats.html
│       ├── agents_list.html
│       ├── agent_detail.html
│       └── model_options.html
├── static/                 # Статические файлы
├── media/                  # Загруженные файлы
└── requirements.txt
```

## Использование

1. **Главная страница** (`/`) - приветствие и переход к playground
2. **Playground** (`/playground/`) - основной интерфейс для работы с ИИ
3. **История** (`/playground/history/`) - просмотр сохраненных сессий
4. **Статистика токенов** (`/playground/token-stats/`) - аналитика использования и расходов
5. **Управление агентами** (`/playground/agents/`) - создание, редактирование и удаление агентов

### Настройки в Playground

- **Модель ИИ**: Выбор из доступных моделей
- **Температура**: Контроль креативности (0.0-2.0)
- **Top P**: Контроль разнообразия (0.0-1.0)
- **Системный промпт**: Настройка поведения модели
- **Загрузка файлов**: Добавление контекста из файлов
- **Сравнение**: Параллельное тестирование моделей

## API Endpoints

- `POST /playground/api/create-session/` - Создание новой сессии
- `POST /playground/api/send-message/` - Отправка сообщения
- `POST /playground/api/upload-file/` - Загрузка файла
- `GET /api/models/` - Получение доступных моделей
- `GET /api/sessions/` - Получение списка сессий
- `GET /api/token-stats/` - Получение статистики токенов
- `POST /api/agents/create/` - Создание нового агента
- `POST /api/agents/<id>/update/` - Обновление агента
- `POST /api/agents/<id>/delete/` - Удаление агента
- `POST /api/agents/<id>/new-session/` - Создание новой сессии для агента

## Система агентов

Приложение поддерживает создание и управление персональными агентами:

### Возможности агентов:
- **Сохранение настроек**: Модель, температура, top_p, системный промпт
- **История чатов**: Каждый агент ведет свою историю сообщений
- **Статистика**: Отслеживание токенов и расходов по каждому агенту
- **Управление**: Создание, редактирование, удаление агентов

### Как использовать:
1. **Создание агента**: В Playground настройте параметры и нажмите "Сохранить как агента"
2. **Управление**: Перейдите в раздел "Агенты" для просмотра всех созданных агентов
3. **Работа с агентом**: Откройте агента для начала чата с сохраненными настройками
4. **Новые сессии**: Создавайте новые сессии для каждого агента

## Сравнение моделей

Приложение поддерживает полноценное сравнение моделей с независимыми настройками:

### Возможности сравнения:
- **Независимые настройки**: Каждая модель может иметь свои параметры (температура, top_p, системный промпт)
- **Отдельные сессии**: Каждое сравнение создает отдельную сессию
- **Статистика токенов**: Отслеживание затрат для каждой модели отдельно
- **Параллельные ответы**: Одновременное получение ответов от разных моделей

### Как использовать:
1. **Включить сравнение**: Нажмите кнопку "Сравнить модели" в Playground
2. **Настроить модели**: Используйте левую панель для основной модели, правую - для сравнения
3. **Отправить сообщения**: Введите сообщение в любое окно чата
4. **Сравнить результаты**: Анализируйте ответы, токены и стоимость каждой модели

## Настройка API ключей

### GigaChat
1. Зарегистрируйтесь на [GigaChat](https://developers.sber.ru/portal/products/gigachat)
2. Получите API ключ и Client Secret
3. Добавьте их в `.env` файл

### Yandex GPT
1. Создайте аккаунт в [Yandex Cloud](https://console.cloud.yandex.ru/)
2. Создайте сервисный аккаунт с ролью `ai.languageModels.user`
3. Получите API ключ для сервисного аккаунта
4. Найдите Folder ID в консоли Yandex Cloud (в разделе "Облако")
5. Добавьте API ключ и Folder ID в `.env` файл

### Perplexity
1. Зарегистрируйтесь на [Perplexity](https://www.perplexity.ai/)
2. Получите API ключ в настройках аккаунта
3. Добавьте его в `.env` файл

## Поддерживаемые форматы файлов

- **Текстовые файлы**: `.txt`
- **Python скрипты**: `.py`
- **PDF документы**: `.pdf`
- **Изображения**: `.jpg`, `.jpeg`, `.png`, `.gif`

## Технологии

- **Backend**: Django 5+, Django REST Framework
- **Frontend**: Bootstrap 5, HTMX, Alpine.js
- **База данных**: PostgreSQL
- **API**: Perplexity, GigaChat, Yandex GPT

## Решение проблем

### Ошибка подключения к PostgreSQL
```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

**Решение:** Используйте SQLite для разработки (по умолчанию) или запустите PostgreSQL:
```bash
# Для Windows (если установлен PostgreSQL)
net start postgresql-x64-13

# Для Linux/Mac
sudo systemctl start postgresql
```

### Ошибка "No changes detected" при makemigrations
**Решение:** Убедитесь, что активировано виртуальное окружение:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Ошибка "The directory 'static' does not exist"
**Решение:** Создайте папку static:
```bash
mkdir static
```

## Разработка

Для разработки рекомендуется:

1. Использовать виртуальное окружение
2. Настроить `.env` файл с тестовыми ключами
3. Использовать `DEBUG=True` для отладки
4. Следить за логами в консоли Django
5. Использовать SQLite для локальной разработки

## Лицензия

MIT License
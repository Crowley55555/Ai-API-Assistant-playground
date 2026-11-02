# AI API Assistant Playground

Django-приложение в духе OpenAI Playground: единый интерфейс для работы с российскими LLM (GigaChat, YandexGPT), сравнение моделей, загрузка файлов для контекста и управление персональными агентами.

## Задача

Собрать в одной веб-песочнице доступ к нескольким LLM-провайдерам, чтобы:
- тестировать и сравнивать ответы разных моделей на одном запросе;
- подкладывать в контекст файлы разных форматов (PDF, изображения, код, таблицы);
- сохранять настройки под задачу в виде «агентов» и возвращаться к ним;
- отслеживать расход токенов по каждой модели.

## Решение

- Чат с LLM по провайдерам **GigaChat** и **YandexGPT** (4 модели: GigaChat Latest/Pro, YandexGPT, YandexGPT Lite).
- Режим сравнения моделей: два независимых чата с собственными параметрами (температура, top_p, системный промпт) бок о бок.
- Загрузка файлов в контекст: `txt`, `py`, `pdf`, `json`, `csv`, `md`, изображения (`jpg`, `png`, `gif`). Текст из PDF извлекается через `PyPDF2`, изображения кодируются в base64.
- Персональные **агенты**: сохранение набора «модель + параметры + системный промпт» с собственной историей сессий.
- **Python-функции (Function Calling)**: пользовательские функции с JSON-описанием и исполняемым кодом, подключаемые к агентам.
- История чатов и аналитика расхода токенов по моделям (через `tiktoken`).
- Адаптивный UI на Bootstrap 5 + HTMX + Alpine.js, тёмная/светлая тема.

## Как устроено

Django-проект с разделением по приложениям:

- `ai_playground/` — настройки, URL-роутинг, WSGI.
- `core/` — главная страница.
- `chat/` — основная логика: модели `ChatSession`, `Message`, `UploadedFile`, `Agent`, `PythonFunction`; сервис `llm_service.py` с единым интерфейсом к GigaChat и YandexGPT; `file_processor.py` для извлечения текста из загрузок; `token_counter.py` для подсчёта токенов.
- `api/` — REST-эндпоинты для списков моделей, сессий и статистики токенов (DRF).
- `templates/` — HTML-страницы playground, истории, статистики, агентов, функций.

Внешние интеграции идут через `requests`: авторизация GigaChat по Basic + получение access-token, YandexGPT по API-ключу сервисного аккаунта и Folder ID.

## Стек

- **Backend:** Python, Django 5, Django REST Framework, django-cors-headers
- **LLM API:** GigaChat (Sber), YandexGPT (Yandex Cloud)
- **Обработка файлов:** PyPDF2, Pillow
- **Токены:** tiktoken
- **БД:** SQLite (по умолчанию) или PostgreSQL (через `psycopg2-binary`, флаг `USE_POSTGRESQL`)
- **Frontend:** Bootstrap 5, HTMX, Alpine.js
- **Конфиг:** python-dotenv

## Результат

- 2 подключённых LLM-провайдера, 4 конфигурируемые модели.
- 5 доменных сущностей в БД (`ChatSession`, `Message`, `UploadedFile`, `Agent`, `PythonFunction`), 12 HTML-шаблонов, ~3 000 строк Python-кода.
- Поддержка 7 форматов файлов (включая изображения) для подкладки в контекст.
- Function Calling: пользователь описывает функцию JSON-схемой и кодом на Python, модель может её вызывать.
- Переключение SQLite ↔ PostgreSQL без правки кода (через переменную окружения).

## Запуск

Требуется Python 3.11+.

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Crowley55555/Ai-API-Assistant-playground.git
cd Ai-API-Assistant-playground

# 2. Создать и активировать виртуальное окружение
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить переменные окружения
cp env.example .env
# затем отредактировать .env и подставить свои ключи:
#   GIGACHAT_API_KEY, GIGACHAT_CLIENT_SECRET, GIGACHAT_SCOPE
#   YANDEX_API_KEY, YANDEX_FOLDER_ID
#   SECRET_KEY, DEBUG
# По умолчанию используется SQLite. Для PostgreSQL:
#   USE_POSTGRESQL=True, DB_NAME, DB_USER, DB_PASSWORD

# 5. Применить миграции
python manage.py migrate

# 6. (опционально) создать суперпользователя для админки
python manage.py createsuperuser

# 7. Запустить сервер
python manage.py runserver
```

Открыть `http://127.0.0.1:8000/` — доступны разделы `/playground/`, `/playground/history/`, `/playground/token-stats/`, `/playground/agents/`, `/playground/functions/`.

### Где взять ключи

- **GigaChat** — [developers.sber.ru/portal/products/gigachat](https://developers.sber.ru/portal/products/gigachat): получить `API Key` и `Client Secret`.
- **YandexGPT** — [console.cloud.yandex.ru](https://console.cloud.yandex.ru): создать сервисный аккаунт с ролью `ai.languageModels.user`, выпустить API-ключ, скопировать Folder ID.

## Автор

Артём Лавров — Python-разработчик (AI-боты и автоматизация для бизнеса)
- Telegram: [@rain511](https://t.me/rain511)
- GitHub: [Crowley55555](https://github.com/Crowley55555)

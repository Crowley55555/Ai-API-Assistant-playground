"""
WSGI config for ai_playground project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_playground.settings')

application = get_wsgi_application()

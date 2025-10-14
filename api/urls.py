from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('models/', views.get_available_models, name='available_models'),
    path('sessions/', views.get_sessions, name='sessions'),
    path('token-stats/', views.get_token_stats, name='token_stats'),
]

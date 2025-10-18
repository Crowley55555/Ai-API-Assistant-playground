from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.playground, name='playground'),
    path('history/', views.history, name='history'),
    path('token-stats/', views.token_stats, name='token_stats'),
    path('agents/', views.agents_list, name='agents_list'),
    path('functions/', views.function_manager, name='function_manager'),
    path('agents/<uuid:agent_id>/', views.agent_detail, name='agent_detail'),
    path('session/<uuid:session_id>/', views.load_session, name='load_session'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('csrf-test/', views.csrf_test, name='csrf_test'),
    path('csrf-simple/', views.csrf_simple, name='csrf_simple'),
    path('api/health/', views.health_check, name='health_check'),
    path('api/send-message/', views.send_message, name='send_message'),
    path('api/create-session/', views.create_session, name='create_session'),
    path('api/update-session/', views.update_session, name='update_session'),
    path('api/upload-file/', views.upload_file, name='upload_file'),
    path('api/session/<str:session_id>/files/', views.get_session_files, name='get_session_files'),
    path('api/agents/create/', views.create_agent, name='create_agent'),
    path('api/agents/check/', views.check_agent_exists, name='check_agent_exists'),
    path('api/agents/<uuid:agent_id>/', views.get_agent, name='get_agent'),
    path('api/agents/<uuid:agent_id>/update/', views.update_agent, name='update_agent'),
    path('api/agents/<uuid:agent_id>/delete/', views.delete_agent, name='delete_agent'),
    path('api/agents/<uuid:agent_id>/new-session/', views.agent_new_session, name='agent_new_session'),
    # Упрощенная система функций - функции создаются только в рамках сессии
]

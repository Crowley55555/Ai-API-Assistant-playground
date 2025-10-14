from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.playground, name='playground'),
    path('history/', views.history, name='history'),
    path('token-stats/', views.token_stats, name='token_stats'),
    path('agents/', views.agents_list, name='agents_list'),
    path('agents/<uuid:agent_id>/', views.agent_detail, name='agent_detail'),
    path('session/<uuid:session_id>/', views.load_session, name='load_session'),
    path('api/send-message/', views.send_message, name='send_message'),
    path('api/create-session/', views.create_session, name='create_session'),
    path('api/upload-file/', views.upload_file, name='upload_file'),
    path('api/agents/create/', views.create_agent, name='create_agent'),
    path('api/agents/<uuid:agent_id>/update/', views.update_agent, name='update_agent'),
    path('api/agents/<uuid:agent_id>/delete/', views.delete_agent, name='delete_agent'),
    path('api/agents/<uuid:agent_id>/new-session/', views.agent_new_session, name='agent_new_session'),
]

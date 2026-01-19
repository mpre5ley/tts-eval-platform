# URL routes for TTS Evaluation Frontend

from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('sessions/', views.sessions, name='sessions'),
    path('metrics/', views.metrics, name='metrics'),
    
    # API proxy endpoints
    path('api/synthesize/', views.synthesize, name='synthesize'),
    path('api/synthesize/batch/', views.synthesize_batch, name='synthesize_batch'),
    path('api/sessions/<uuid:session_id>/', views.get_session, name='get_session'),
    path('api/metrics/provider/<str:provider_id>/', views.get_provider_metrics, name='get_provider_metrics'),
    path('api/metrics/comparison/', views.get_comparison_metrics, name='get_comparison_metrics'),
    path('api/benchmarks/create/', views.create_benchmark, name='create_benchmark'),
    path('api/health/', views.health, name='health'),
]

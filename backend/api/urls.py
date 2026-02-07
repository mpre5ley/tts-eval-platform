# URL routes for TTS Evaluation Platform API

from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Provider endpoints
    path('providers/', views.get_providers, name='get_providers'),
    path('providers/<str:provider_id>/voices/', views.get_provider_voices, name='get_provider_voices'),
    
    # Synthesis endpoints
    path('synthesize/', views.synthesize, name='synthesize'),
    path('synthesize/batch/', views.synthesize_batch, name='synthesize_batch'),
    
    # Batch CSV upload endpoints
    path('batch/upload/', views.batch_csv_upload, name='batch_csv_upload'),
    path('batch/execute/', views.batch_execute_task, name='batch_execute_task'),
    
    # Evaluation endpoints
    path('sessions/', views.get_sessions, name='get_sessions'),
    path('sessions/<uuid:session_id>/', views.get_session, name='get_session'),
    path('evaluations/', views.get_evaluations, name='get_evaluations'),
    path('evaluations/<int:evaluation_id>/', views.get_evaluation, name='get_evaluation'),
    
    # Metrics endpoints
    path('metrics/provider/<str:provider_id>/', views.get_provider_metrics, name='get_provider_metrics'),
    path('metrics/comparison/', views.get_comparison_metrics, name='get_comparison_metrics'),
    path('metrics/reset/', views.reset_metrics, name='reset_metrics'),
    
    # Benchmark endpoints
    path('benchmarks/', views.get_benchmarks, name='get_benchmarks'),
    path('benchmarks/create/', views.create_benchmark, name='create_benchmark'),
    path('benchmarks/<uuid:benchmark_id>/', views.get_benchmark, name='get_benchmark'),
]

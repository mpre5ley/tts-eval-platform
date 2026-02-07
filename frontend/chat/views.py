# Views for TTS Evaluation Frontend

import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
import json


def index(request):
    """Main TTS evaluation interface"""
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/providers/", timeout=10)
        providers_data = response.json() if response.status_code == 200 else {'providers': []}
    except requests.RequestException:
        providers_data = {'providers': []}
    
    return render(request, 'chat/index.html', {
        'providers': providers_data.get('providers', [])
    })


def sessions(request):
    """View evaluation sessions history"""
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/sessions/", timeout=10)
        sessions_data = response.json() if response.status_code == 200 else []
    except requests.RequestException:
        sessions_data = []
    
    return render(request, 'chat/sessions.html', {'sessions': sessions_data})


def metrics(request):
    """View provider comparison metrics"""
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/metrics/comparison/", timeout=10)
        metrics_data = response.json() if response.status_code == 200 else {'providers': []}
    except requests.RequestException:
        metrics_data = {'providers': []}
    
    return render(request, 'chat/metrics.html', {'metrics': metrics_data.get('providers', [])})


@require_http_methods(["POST"])
def synthesize(request):
    """Handle single TTS synthesis request"""
    try:
        data = json.loads(request.body)
        
        response = requests.post(
            f"{settings.BACKEND_API_URL}/synthesize/",
            json=data,
            timeout=120
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_http_methods(["POST"])
def synthesize_batch(request):
    """Handle batch TTS synthesis request (multiple providers)"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        providers = data.get('providers', [])
        streaming = data.get('streaming', False)
        session_name = data.get('session_name', '')
        
        if not text:
            return JsonResponse({'error': 'Text is required'}, status=400)
        
        if not providers:
            return JsonResponse({'error': 'At least one provider configuration is required'}, status=400)
        
        response = requests.post(
            f"{settings.BACKEND_API_URL}/synthesize/batch/",
            json={
                'text': text,
                'providers': providers,
                'streaming': streaming,
                'session_name': session_name,
            },
            timeout=180
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_http_methods(["GET"])
def get_session(request, session_id):
    """Get details of a specific evaluation session"""
    try:
        response = requests.get(
            f"{settings.BACKEND_API_URL}/sessions/{session_id}/",
            timeout=10
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)


@require_http_methods(["GET"])
def get_provider_metrics(request, provider_id):
    """Get metrics for a specific provider"""
    try:
        response = requests.get(
            f"{settings.BACKEND_API_URL}/metrics/provider/{provider_id}/",
            timeout=10
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)


@require_http_methods(["GET"])
def get_comparison_metrics(request):
    """Get comparison metrics across all providers"""
    try:
        response = requests.get(
            f"{settings.BACKEND_API_URL}/metrics/comparison/",
            timeout=10
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)


@require_http_methods(["POST"])
def create_benchmark(request):
    """Create a new benchmark run"""
    try:
        data = json.loads(request.body)
        
        response = requests.post(
            f"{settings.BACKEND_API_URL}/benchmarks/create/",
            json=data,
            timeout=300
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_http_methods(["POST"])
def reset_metrics(request):
    """Reset all stored metrics"""
    try:
        response = requests.post(
            f"{settings.BACKEND_API_URL}/metrics/reset/",
            timeout=30
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)


@require_http_methods(["GET"])
def health(request):
    """Check backend health status"""
    try:
        response = requests.get(f"{settings.BACKEND_API_URL}/health/", timeout=5)
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)


@require_http_methods(["POST"])
def batch_csv_upload(request):
    """Handle CSV file upload for batch testing"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        csv_file = request.FILES['file']
        providers = request.POST.get('providers', '')
        session_name = request.POST.get('session_name', '')
        
        # Forward the file and form data to the backend
        files = {'file': (csv_file.name, csv_file.read(), csv_file.content_type)}
        data = {
            'providers': providers,
            'session_name': session_name
        }
        response = requests.post(
            f"{settings.BACKEND_API_URL}/batch/upload/",
            files=files,
            data=data,
            timeout=30
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)


@require_http_methods(["POST"])
def batch_execute_task(request):
    """Execute a single batch task"""
    try:
        data = json.loads(request.body)
        
        response = requests.post(
            f"{settings.BACKEND_API_URL}/batch/execute/",
            json=data,
            timeout=120
        )
        return JsonResponse(response.json(), status=response.status_code)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Backend connection error: {str(e)}'}, status=503)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

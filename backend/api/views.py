# Views for TTS Evaluation Platform API Endpoints

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Min, Max, Count, F
from django.http import StreamingHttpResponse
import statistics
from dataclasses import asdict

from .serializers import (
    SynthesisRequestSerializer,
    BatchSynthesisRequestSerializer,
    EvaluationRequestSerializer,
    BenchmarkRequestSerializer,
    SynthesisResponseSerializer,
    BatchSynthesisResponseSerializer,
    TTSEvaluationSerializer,
    TTSEvaluationSummarySerializer,
    EvaluationSessionSerializer,
    EvaluationSessionListSerializer,
    TTSProviderSerializer,
    VoiceListSerializer,
    ProviderInfoSerializer,
    ProviderMetricsAggregateSerializer,
    ComparisonMetricsSerializer,
    BenchmarkRunSerializer,
)
from .services import TTSServiceManager, TTSMetrics, TTSResult
from .models import (
    TTSProvider, Voice, EvaluationSession, TTSEvaluation,
    BenchmarkRun, ProviderMetricsAggregate
)


# ========== Provider Endpoints ==========

@api_view(['GET'])
def get_providers(request):
    """Get all available TTS providers with their voices"""
    providers_data = []
    
    for provider_id, config in settings.TTS_PROVIDERS.items():
        provider = TTSServiceManager.get_provider(provider_id)
        if provider:
            voices = provider.get_voices()
            providers_data.append({
                'provider_id': provider_id,
                'name': provider.provider_name,
                'description': config.get('description', ''),
                'is_enabled': config.get('enabled', True),
                'demo_mode': provider.demo_mode,
                'voices': [
                    {
                        'voice_id': v['voice_id'],
                        'name': v['name'],
                        'language': v.get('language', 'en-US'),
                        'gender': v.get('gender', 'neutral'),
                        'description': v.get('description', ''),
                        'provider_id': provider_id,
                        'provider_name': provider.provider_name,
                    }
                    for v in voices
                ]
            })
    
    return Response({'providers': providers_data})


@api_view(['GET'])
def get_provider_voices(request, provider_id):
    """Get voices for a specific provider"""
    provider = TTSServiceManager.get_provider(provider_id)
    if not provider:
        return Response(
            {'error': f'Unknown provider: {provider_id}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    voices = provider.get_voices()
    voice_data = [
        {
            'voice_id': v['voice_id'],
            'name': v['name'],
            'language': v.get('language', 'en-US'),
            'gender': v.get('gender', 'neutral'),
            'description': v.get('description', ''),
            'provider_id': provider_id,
            'provider_name': provider.provider_name,
        }
        for v in voices
    ]
    
    return Response({
        'provider_id': provider_id,
        'provider_name': provider.provider_name,
        'demo_mode': provider.demo_mode,
        'voices': voice_data
    })


# ========== Synthesis Endpoints ==========

@api_view(['POST'])
def synthesize(request):
    """Synthesize text using a single TTS provider"""
    serializer = SynthesisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    provider_id = data['provider_id']
    text = data['text']
    voice_id = data['voice_id']
    streaming = data.get('streaming', False)
    
    # Build provider options
    options = {}
    if data.get('model_id'):
        options['model_id'] = data['model_id']
    if data.get('language_code'):
        options['language_code'] = data['language_code']
    if data.get('speaking_rate'):
        options['speaking_rate'] = data['speaking_rate']
    if data.get('pitch'):
        options['pitch'] = data['pitch']
    if data.get('stability') is not None:
        options['voice_settings'] = {
            'stability': data.get('stability', 0.5),
            'similarity_boost': data.get('similarity_boost', 0.75),
        }
    
    # Perform synthesis
    result = TTSServiceManager.synthesize(provider_id, text, voice_id, streaming, **options)
    
    provider = TTSServiceManager.get_provider(provider_id)
    
    response_data = {
        'success': result.success,
        'provider_id': result.provider_id,
        'provider_name': provider.provider_name if provider else provider_id,
        'voice_id': result.voice_id,
        'model_id': result.model_id,
        'audio_base64': result.audio_base64 or '',
        'audio_format': result.metrics.audio_format,
        'metrics': {
            'time_to_first_byte': result.metrics.time_to_first_byte,
            'time_to_first_audio': result.metrics.time_to_first_audio,
            'total_synthesis_time': result.metrics.total_synthesis_time,
            'network_latency': result.metrics.network_latency,
            'audio_duration': result.metrics.audio_duration,
            'audio_size': result.metrics.audio_size,
            'audio_format': result.metrics.audio_format,
            'sample_rate': result.metrics.sample_rate,
            'bitrate': result.metrics.bitrate,
            'is_streaming': result.metrics.is_streaming,
            'chunk_count': result.metrics.chunk_count,
            'avg_chunk_size': result.metrics.avg_chunk_size,
            'playback_jitter': result.metrics.playback_jitter,
            'min_chunk_delay': result.metrics.min_chunk_delay,
            'max_chunk_delay': result.metrics.max_chunk_delay,
            'avg_chunk_delay': result.metrics.avg_chunk_delay,
            'character_count': result.metrics.character_count,
            'word_count': result.metrics.word_count,
            'chars_per_second': result.metrics.chars_per_second,
            'realtime_factor': result.metrics.realtime_factor,
        },
        'error_message': result.error_message,
    }
    
    return Response(response_data)


@api_view(['POST'])
def synthesize_batch(request):
    """Synthesize text using multiple TTS providers"""
    serializer = BatchSynthesisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    text = data['text']
    providers = data['providers']
    streaming = data.get('streaming', False)
    session_name = data.get('session_name', '')
    
    # Generate default session name if not provided
    if not session_name:
        session_name = f"tts_eval_{timezone.now().strftime('%d%m%y')}"
    
    # Create evaluation session
    session = EvaluationSession.objects.create(
        text=text,
        name=session_name,
        status='running'
    )
    
    results = []
    
    for provider_config in providers:
        provider_id = provider_config['provider_id']
        voice_id = provider_config['voice_id']
        options = provider_config.get('options', {})
        
        # Perform synthesis
        result = TTSServiceManager.synthesize(provider_id, text, voice_id, streaming, **options)
        
        provider = TTSServiceManager.get_provider(provider_id)
        
        # Look up voice name from provider's available voices
        voice_name = voice_id  # Default to voice_id if name not found
        if provider:
            voices = provider.get_voices()
            for v in voices:
                if v.get('voice_id') == voice_id:
                    voice_name = v.get('name', voice_id)
                    break
        
        # Get or create provider in database
        db_provider, _ = TTSProvider.objects.get_or_create(
            provider_id=provider_id,
            defaults={
                'name': provider.provider_name if provider else provider_id,
                'description': settings.TTS_PROVIDERS.get(provider_id, {}).get('description', ''),
            }
        )
        
        # Create evaluation record
        evaluation = TTSEvaluation.objects.create(
            session=session,
            provider=db_provider,
            voice_id_str=voice_id,
            voice_name=voice_name,
            model_id=result.model_id,
            success=result.success,
            error_message=result.error_message,
            time_to_first_byte=result.metrics.time_to_first_byte,
            time_to_first_audio=result.metrics.time_to_first_audio,
            total_synthesis_time=result.metrics.total_synthesis_time,
            network_latency=result.metrics.network_latency,
            audio_duration=result.metrics.audio_duration,
            audio_size=result.metrics.audio_size,
            audio_format=result.metrics.audio_format,
            sample_rate=result.metrics.sample_rate,
            bitrate=result.metrics.bitrate,
            is_streaming=result.metrics.is_streaming,
            chunk_count=result.metrics.chunk_count,
            avg_chunk_size=result.metrics.avg_chunk_size,
            chunk_timings=result.metrics.chunk_timings,
            playback_jitter=result.metrics.playback_jitter,
            min_chunk_delay=result.metrics.min_chunk_delay,
            max_chunk_delay=result.metrics.max_chunk_delay,
            avg_chunk_delay=result.metrics.avg_chunk_delay,
            character_count=result.metrics.character_count,
            word_count=result.metrics.word_count,
            chars_per_second=result.metrics.chars_per_second,
            realtime_factor=result.metrics.realtime_factor,
            request_params=options,
            response_headers=result.response_headers,
            audio_base64=result.audio_base64 or '',
        )
        
        results.append({
            'success': result.success,
            'provider_id': result.provider_id,
            'provider_name': provider.provider_name if provider else provider_id,
            'voice_id': result.voice_id,
            'model_id': result.model_id,
            'audio_base64': result.audio_base64 or '',
            'audio_format': result.metrics.audio_format,
            'metrics': {
                'time_to_first_byte': result.metrics.time_to_first_byte,
                'time_to_first_audio': result.metrics.time_to_first_audio,
                'total_synthesis_time': result.metrics.total_synthesis_time,
                'network_latency': result.metrics.network_latency,
                'audio_duration': result.metrics.audio_duration,
                'audio_size': result.metrics.audio_size,
                'audio_format': result.metrics.audio_format,
                'sample_rate': result.metrics.sample_rate,
                'bitrate': result.metrics.bitrate,
                'is_streaming': result.metrics.is_streaming,
                'chunk_count': result.metrics.chunk_count,
                'avg_chunk_size': result.metrics.avg_chunk_size,
                'playback_jitter': result.metrics.playback_jitter,
                'min_chunk_delay': result.metrics.min_chunk_delay,
                'max_chunk_delay': result.metrics.max_chunk_delay,
                'avg_chunk_delay': result.metrics.avg_chunk_delay,
                'character_count': result.metrics.character_count,
                'word_count': result.metrics.word_count,
                'chars_per_second': result.metrics.chars_per_second,
                'realtime_factor': result.metrics.realtime_factor,
            },
            'error_message': result.error_message,
            'evaluation_id': evaluation.id,
        })
    
    # Update session status
    session.status = 'completed'
    session.completed_at = timezone.now()
    session.save()
    
    return Response({
        'session_id': str(session.session_id),
        'text': text,
        'results': results,
        'timestamp': session.created_at,
    })


# ========== Evaluation Endpoints ==========

@api_view(['GET'])
def get_sessions(request):
    """Get list of evaluation sessions"""
    limit = int(request.query_params.get('limit', 20))
    sessions = EvaluationSession.objects.all()[:limit]
    serializer = EvaluationSessionListSerializer(sessions, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_session(request, session_id):
    """Get a specific evaluation session with all evaluations"""
    try:
        session = EvaluationSession.objects.get(session_id=session_id)
    except EvaluationSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = EvaluationSessionSerializer(session)
    return Response(serializer.data)


@api_view(['GET'])
def get_evaluation(request, evaluation_id):
    """Get a specific evaluation with full details"""
    try:
        evaluation = TTSEvaluation.objects.get(id=evaluation_id)
    except TTSEvaluation.DoesNotExist:
        return Response(
            {'error': 'Evaluation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = TTSEvaluationSerializer(evaluation)
    return Response(serializer.data)


@api_view(['GET'])
def get_evaluations(request):
    """Get list of evaluations with optional filtering"""
    provider_id = request.query_params.get('provider_id')
    success_only = request.query_params.get('success_only', 'false').lower() == 'true'
    limit = int(request.query_params.get('limit', 50))
    
    evaluations = TTSEvaluation.objects.all()
    
    if provider_id:
        evaluations = evaluations.filter(provider__provider_id=provider_id)
    
    if success_only:
        evaluations = evaluations.filter(success=True)
    
    evaluations = evaluations[:limit]
    serializer = TTSEvaluationSummarySerializer(evaluations, many=True)
    return Response(serializer.data)


# ========== Metrics Endpoints ==========

@api_view(['GET'])
def get_provider_metrics(request, provider_id):
    """Get aggregated metrics for a specific provider"""
    evaluations = TTSEvaluation.objects.filter(
        provider__provider_id=provider_id,
        success=True
    )
    
    if not evaluations.exists():
        return Response({
            'provider_id': provider_id,
            'total_evaluations': 0,
            'message': 'No successful evaluations found'
        })
    
    # Calculate aggregates
    agg = evaluations.aggregate(
        total=Count('id'),
        avg_ttfb=Avg('time_to_first_byte'),
        avg_ttfa=Avg('time_to_first_audio'),
        avg_total=Avg('total_synthesis_time'),
        avg_jitter=Avg('playback_jitter'),
        avg_rtf=Avg('realtime_factor'),
        min_total=Min('total_synthesis_time'),
        max_total=Max('total_synthesis_time'),
    )
    
    # Calculate percentiles
    synthesis_times = list(evaluations.values_list('total_synthesis_time', flat=True))
    synthesis_times = [t for t in synthesis_times if t is not None]
    synthesis_times.sort()
    
    p50 = p95 = p99 = None
    if synthesis_times:
        n = len(synthesis_times)
        p50 = synthesis_times[int(n * 0.5)]
        p95 = synthesis_times[int(n * 0.95)] if n >= 20 else None
        p99 = synthesis_times[int(n * 0.99)] if n >= 100 else None
    
    # Success rate
    total_all = TTSEvaluation.objects.filter(provider__provider_id=provider_id).count()
    success_rate = (agg['total'] / total_all * 100) if total_all > 0 else 0
    
    provider = TTSServiceManager.get_provider(provider_id)
    
    return Response({
        'provider_id': provider_id,
        'provider_name': provider.provider_name if provider else provider_id,
        'total_evaluations': total_all,
        'successful_evaluations': agg['total'],
        'success_rate': round(success_rate, 2),
        'avg_time_to_first_byte': round(agg['avg_ttfb'], 2) if agg['avg_ttfb'] else None,
        'avg_time_to_first_audio': round(agg['avg_ttfa'], 2) if agg['avg_ttfa'] else None,
        'avg_total_synthesis_time': round(agg['avg_total'], 2) if agg['avg_total'] else None,
        'avg_playback_jitter': round(agg['avg_jitter'], 2) if agg['avg_jitter'] else None,
        'avg_realtime_factor': round(agg['avg_rtf'], 2) if agg['avg_rtf'] else None,
        'min_synthesis_time': round(agg['min_total'], 2) if agg['min_total'] else None,
        'max_synthesis_time': round(agg['max_total'], 2) if agg['max_total'] else None,
        'p50_synthesis_time': round(p50, 2) if p50 else None,
        'p95_synthesis_time': round(p95, 2) if p95 else None,
        'p99_synthesis_time': round(p99, 2) if p99 else None,
    })


@api_view(['GET'])
def get_comparison_metrics(request):
    """Get comparison metrics across all providers"""
    provider_ids = request.query_params.getlist('provider_ids')
    
    if not provider_ids:
        # Get all providers with evaluations (use set to ensure uniqueness)
        provider_ids = list(set(
            TTSEvaluation.objects
            .values_list('provider__provider_id', flat=True)
        ))
    
    comparison_data = []
    
    for pid in provider_ids:
        evaluations = TTSEvaluation.objects.filter(
            provider__provider_id=pid,
            success=True
        )
        
        if not evaluations.exists():
            continue
        
        agg = evaluations.aggregate(
            total=Count('id'),
            avg_ttfb=Avg('time_to_first_byte'),
            avg_ttfa=Avg('time_to_first_audio'),
            avg_total=Avg('total_synthesis_time'),
            avg_jitter=Avg('playback_jitter'),
        )
        
        synthesis_times = list(evaluations.values_list('total_synthesis_time', flat=True))
        synthesis_times = [t for t in synthesis_times if t is not None]
        synthesis_times.sort()
        
        p50 = p95 = p99 = None
        if synthesis_times:
            n = len(synthesis_times)
            p50 = synthesis_times[int(n * 0.5)]
            p95 = synthesis_times[int(n * 0.95)] if n >= 20 else None
            p99 = synthesis_times[int(n * 0.99)] if n >= 100 else None
        
        total_all = TTSEvaluation.objects.filter(provider__provider_id=pid).count()
        success_rate = (agg['total'] / total_all * 100) if total_all > 0 else 0
        
        provider = TTSServiceManager.get_provider(pid)
        
        comparison_data.append({
            'provider_id': pid,
            'provider_name': provider.provider_name if provider else pid,
            'avg_ttfb': round(agg['avg_ttfb'], 2) if agg['avg_ttfb'] else None,
            'avg_ttfa': round(agg['avg_ttfa'], 2) if agg['avg_ttfa'] else None,
            'avg_total_time': round(agg['avg_total'], 2) if agg['avg_total'] else None,
            'avg_jitter': round(agg['avg_jitter'], 2) if agg['avg_jitter'] else None,
            'p50_time': round(p50, 2) if p50 else None,
            'p95_time': round(p95, 2) if p95 else None,
            'p99_time': round(p99, 2) if p99 else None,
            'total_evaluations': total_all,
            'success_rate': round(success_rate, 2),
        })
    
    # Sort by average total synthesis time
    comparison_data.sort(key=lambda x: x.get('avg_total_time') or float('inf'))
    
    return Response({'providers': comparison_data})


# ========== Benchmark Endpoints ==========

@api_view(['POST'])
def create_benchmark(request):
    """Create and run a benchmark"""
    serializer = BenchmarkRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    # Create benchmark
    benchmark = BenchmarkRun.objects.create(
        name=data['name'],
        description=data.get('description', ''),
        test_texts=data['test_texts'],
        iterations=data.get('iterations', 3),
        status='running',
        started_at=timezone.now()
    )
    
    results_summary = {
        'providers': {},
        'test_results': []
    }
    
    # Run benchmark
    for text in data['test_texts']:
        for iteration in range(data.get('iterations', 3)):
            for provider_config in data['provider_configs']:
                provider_id = provider_config['provider_id']
                voice_id = provider_config['voice_id']
                options = provider_config.get('options', {})
                
                # Perform synthesis
                result = TTSServiceManager.synthesize(
                    provider_id, text, voice_id, False, **options
                )
                
                # Store result
                if provider_id not in results_summary['providers']:
                    results_summary['providers'][provider_id] = {
                        'synthesis_times': [],
                        'ttfa_times': [],
                        'jitter_values': [],
                        'successes': 0,
                        'failures': 0,
                    }
                
                if result.success:
                    results_summary['providers'][provider_id]['successes'] += 1
                    if result.metrics.total_synthesis_time:
                        results_summary['providers'][provider_id]['synthesis_times'].append(
                            result.metrics.total_synthesis_time
                        )
                    if result.metrics.time_to_first_audio:
                        results_summary['providers'][provider_id]['ttfa_times'].append(
                            result.metrics.time_to_first_audio
                        )
                    if result.metrics.playback_jitter:
                        results_summary['providers'][provider_id]['jitter_values'].append(
                            result.metrics.playback_jitter
                        )
                else:
                    results_summary['providers'][provider_id]['failures'] += 1
    
    # Calculate summary statistics
    for provider_id, data in results_summary['providers'].items():
        times = data['synthesis_times']
        if times:
            data['avg_synthesis_time'] = statistics.mean(times)
            data['min_synthesis_time'] = min(times)
            data['max_synthesis_time'] = max(times)
            data['std_synthesis_time'] = statistics.stdev(times) if len(times) > 1 else 0
        
        ttfa = data['ttfa_times']
        if ttfa:
            data['avg_ttfa'] = statistics.mean(ttfa)
        
        jitter = data['jitter_values']
        if jitter:
            data['avg_jitter'] = statistics.mean(jitter)
        
        total = data['successes'] + data['failures']
        data['success_rate'] = (data['successes'] / total * 100) if total > 0 else 0
    
    # Update benchmark
    benchmark.results_summary = results_summary
    benchmark.status = 'completed'
    benchmark.completed_at = timezone.now()
    benchmark.save()
    
    return Response({
        'benchmark_id': str(benchmark.benchmark_id),
        'name': benchmark.name,
        'status': benchmark.status,
        'results_summary': results_summary,
        'created_at': benchmark.created_at,
        'completed_at': benchmark.completed_at,
    })


@api_view(['GET'])
def get_benchmarks(request):
    """Get list of benchmarks"""
    limit = int(request.query_params.get('limit', 10))
    benchmarks = BenchmarkRun.objects.all()[:limit]
    serializer = BenchmarkRunSerializer(benchmarks, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_benchmark(request, benchmark_id):
    """Get a specific benchmark"""
    try:
        benchmark = BenchmarkRun.objects.get(benchmark_id=benchmark_id)
    except BenchmarkRun.DoesNotExist:
        return Response(
            {'error': 'Benchmark not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = BenchmarkRunSerializer(benchmark)
    return Response(serializer.data)


# ========== Health Check ==========

@api_view(['GET'])
def health_check(request):
    """API health check endpoint"""
    providers_status = {}
    
    for provider_id in settings.TTS_PROVIDERS.keys():
        provider = TTSServiceManager.get_provider(provider_id)
        if provider:
            providers_status[provider_id] = {
                'name': provider.provider_name,
                'demo_mode': provider.demo_mode,
                'status': 'available' if not provider.demo_mode else 'demo_mode'
            }
    
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'providers': providers_status
    })


# Decorator to accept GET requests
# Return session by session id
@api_view(['GET'])
def get_session(request, session_id):
    try:
        session = EvaluationSession.objects.get(session_id=session_id)
        serializer = EvaluationSessionSerializer(session)
        return Response(serializer.data)
    except EvaluationSession.DoesNotExist:
        return Response(
            {'error': 'Session not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
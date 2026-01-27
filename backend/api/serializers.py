# Serializers for TTS Evaluation Platform API

from rest_framework import serializers
from .models import (
    TTSProvider, Voice, EvaluationSession, TTSEvaluation, 
    BenchmarkRun, ProviderMetricsAggregate
)


# ========== Provider Serializers ==========

class TTSProviderSerializer(serializers.ModelSerializer):
    """Serializer for TTS Provider model"""
    voice_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TTSProvider
        fields = [
            'id', 'provider_id', 'name', 'description', 'is_enabled',
            'api_base_url', 'config', 'voice_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_voice_count(self, obj):
        return obj.voices.filter(is_available=True).count()


class VoiceSerializer(serializers.ModelSerializer):
    """Serializer for Voice model"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_id_str = serializers.CharField(source='provider.provider_id', read_only=True)
    
    class Meta:
        model = Voice
        fields = [
            'id', 'provider', 'provider_name', 'provider_id_str', 'voice_id', 
            'name', 'language', 'gender', 'description', 'is_available', 'settings'
        ]


class VoiceListSerializer(serializers.Serializer):
    """Lightweight serializer for voice listing"""
    voice_id = serializers.CharField()
    name = serializers.CharField()
    language = serializers.CharField()
    gender = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    provider_id = serializers.CharField()
    provider_name = serializers.CharField()


# ========== Evaluation Serializers ==========

class TTSEvaluationSerializer(serializers.ModelSerializer):
    """Full serializer for TTS Evaluation model"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_id_str = serializers.CharField(source='provider.provider_id', read_only=True)
    voice_name = serializers.CharField(source='voice.name', read_only=True, allow_null=True)
    
    class Meta:
        model = TTSEvaluation
        fields = [
            'id', 'session', 'provider', 'provider_name', 'provider_id_str',
            'voice', 'voice_name', 'voice_id_str', 'model_id', 'success', 'error_message',
            # Latency metrics
            'time_to_first_byte', 'time_to_first_audio', 'total_synthesis_time', 'network_latency',
            # Audio metrics
            'audio_duration', 'audio_size', 'audio_format', 'sample_rate', 'bitrate',
            # Streaming metrics
            'is_streaming', 'chunk_count', 'avg_chunk_size', 'chunk_timings',
            # Jitter metrics
            'playback_jitter', 'min_chunk_delay', 'max_chunk_delay', 'avg_chunk_delay',
            # Request metadata
            'request_params', 'response_headers', 'character_count', 'word_count',
            # Computed metrics
            'chars_per_second', 'realtime_factor',
            # Audio data
            'audio_file_path', 'audio_base64',
            # Timestamps
            'created_at'
        ]
        read_only_fields = ['created_at']


class TTSEvaluationSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for evaluation summaries"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    
    class Meta:
        model = TTSEvaluation
        fields = [
            'id', 'provider_name', 'voice_id_str', 'voice_name', 'success',
            'time_to_first_audio', 'total_synthesis_time', 'playback_jitter',
            'audio_duration', 'realtime_factor', 'created_at'
        ]


class EvaluationSessionSerializer(serializers.ModelSerializer):
    """Full serializer for Evaluation Session model"""
    evaluations = TTSEvaluationSummarySerializer(many=True, read_only=True)
    evaluation_count = serializers.IntegerField(read_only=True)
    successful_evaluations = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = EvaluationSession
        fields = [
            'id', 'session_id', 'name', 'text', 'notes', 'status',
            'created_at', 'completed_at', 'evaluation_count', 
            'successful_evaluations', 'evaluations'
        ]
        read_only_fields = ['session_id', 'created_at']


class EvaluationSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for session listing"""
    evaluation_count = serializers.IntegerField(read_only=True)
    successful_evaluations = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = EvaluationSession
        fields = [
            'id', 'session_id', 'name', 'text', 'status',
            'created_at', 'completed_at', 'evaluation_count', 'successful_evaluations'
        ]


# ========== Request Serializers ==========

class SynthesisRequestSerializer(serializers.Serializer):
    """Serializer for TTS synthesis requests"""
    text = serializers.CharField(max_length=5000, help_text='Text to synthesize')
    provider_id = serializers.CharField(max_length=50, help_text='TTS provider ID')
    voice_id = serializers.CharField(max_length=100, help_text='Voice ID for synthesis')
    streaming = serializers.BooleanField(default=False, help_text='Use streaming mode')
    
    # Optional provider-specific parameters
    model_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    language_code = serializers.CharField(max_length=20, required=False, default='en-US')
    speaking_rate = serializers.FloatField(min_value=0.25, max_value=4.0, required=False, default=1.0)
    pitch = serializers.FloatField(min_value=-20.0, max_value=20.0, required=False, default=0.0)
    
    # ElevenLabs specific
    stability = serializers.FloatField(min_value=0.0, max_value=1.0, required=False, default=0.5)
    similarity_boost = serializers.FloatField(min_value=0.0, max_value=1.0, required=False, default=0.75)


class BatchSynthesisRequestSerializer(serializers.Serializer):
    """Serializer for batch TTS synthesis requests"""
    text = serializers.CharField(max_length=5000, help_text='Text to synthesize')
    providers = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=10,
        help_text='List of provider configurations'
    )
    streaming = serializers.BooleanField(default=False)
    session_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    def validate_providers(self, value):
        """Validate provider configurations"""
        for provider_config in value:
            if 'provider_id' not in provider_config:
                raise serializers.ValidationError("Each provider must have a 'provider_id'")
            if 'voice_id' not in provider_config:
                raise serializers.ValidationError("Each provider must have a 'voice_id'")
        return value


class EvaluationRequestSerializer(serializers.Serializer):
    """Serializer for evaluation requests"""
    text = serializers.CharField(max_length=5000)
    provider_configs = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=10
    )
    streaming = serializers.BooleanField(default=False)
    session_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    iterations = serializers.IntegerField(min_value=1, max_value=10, default=1)


# ========== Response Serializers ==========

class MetricsResponseSerializer(serializers.Serializer):
    """Serializer for synthesis metrics response"""
    # Timing metrics (ms)
    time_to_first_byte = serializers.FloatField(allow_null=True)
    time_to_first_audio = serializers.FloatField(allow_null=True)
    total_synthesis_time = serializers.FloatField(allow_null=True)
    network_latency = serializers.FloatField(allow_null=True)
    
    # Audio metrics
    audio_duration = serializers.FloatField(allow_null=True)
    audio_size = serializers.IntegerField(allow_null=True)
    audio_format = serializers.CharField()
    sample_rate = serializers.IntegerField(allow_null=True)
    bitrate = serializers.IntegerField(allow_null=True)
    
    # Streaming metrics
    is_streaming = serializers.BooleanField()
    chunk_count = serializers.IntegerField(allow_null=True)
    avg_chunk_size = serializers.FloatField(allow_null=True)
    
    # Jitter metrics
    playback_jitter = serializers.FloatField(allow_null=True)
    min_chunk_delay = serializers.FloatField(allow_null=True)
    max_chunk_delay = serializers.FloatField(allow_null=True)
    avg_chunk_delay = serializers.FloatField(allow_null=True)
    
    # Text metrics
    character_count = serializers.IntegerField()
    word_count = serializers.IntegerField()
    
    # Computed metrics
    chars_per_second = serializers.FloatField(allow_null=True)
    realtime_factor = serializers.FloatField(allow_null=True)


class SynthesisResponseSerializer(serializers.Serializer):
    """Serializer for TTS synthesis response"""
    success = serializers.BooleanField()
    provider_id = serializers.CharField()
    provider_name = serializers.CharField()
    voice_id = serializers.CharField()
    model_id = serializers.CharField(allow_blank=True)
    audio_base64 = serializers.CharField(allow_blank=True)
    audio_format = serializers.CharField()
    metrics = MetricsResponseSerializer()
    error_message = serializers.CharField(allow_blank=True)


class BatchSynthesisResponseSerializer(serializers.Serializer):
    """Serializer for batch synthesis response"""
    session_id = serializers.UUIDField()
    text = serializers.CharField()
    results = SynthesisResponseSerializer(many=True)
    timestamp = serializers.DateTimeField()


# ========== Benchmark Serializers ==========

class BenchmarkRunSerializer(serializers.ModelSerializer):
    """Full serializer for Benchmark Run model"""
    providers = TTSProviderSerializer(many=True, read_only=True)
    provider_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = BenchmarkRun
        fields = [
            'id', 'benchmark_id', 'name', 'description', 'test_texts',
            'providers', 'provider_ids', 'iterations', 'status',
            'results_summary', 'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['benchmark_id', 'status', 'results_summary', 'created_at', 'started_at', 'completed_at']


class BenchmarkRequestSerializer(serializers.Serializer):
    """Serializer for benchmark requests"""
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    test_texts = serializers.ListField(
        child=serializers.CharField(max_length=5000),
        min_length=1,
        max_length=20
    )
    provider_configs = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=10
    )
    iterations = serializers.IntegerField(min_value=1, max_value=10, default=3)


# ========== Aggregate Metrics Serializers ==========

class ProviderMetricsAggregateSerializer(serializers.ModelSerializer):
    """Serializer for Provider Metrics Aggregate model"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_id_str = serializers.CharField(source='provider.provider_id', read_only=True)
    
    class Meta:
        model = ProviderMetricsAggregate
        fields = [
            'id', 'provider', 'provider_name', 'provider_id_str',
            'total_evaluations', 'successful_evaluations', 'success_rate',
            'avg_time_to_first_byte', 'avg_time_to_first_audio',
            'avg_total_synthesis_time', 'avg_playback_jitter', 'avg_realtime_factor',
            'p50_synthesis_time', 'p95_synthesis_time', 'p99_synthesis_time',
            'min_synthesis_time', 'max_synthesis_time', 'updated_at'
        ]


class ComparisonMetricsSerializer(serializers.Serializer):
    """Serializer for provider comparison metrics"""
    provider_id = serializers.CharField()
    provider_name = serializers.CharField()
    
    # Averages
    avg_ttfb = serializers.FloatField(allow_null=True)
    avg_ttfa = serializers.FloatField(allow_null=True)
    avg_total_time = serializers.FloatField(allow_null=True)
    avg_jitter = serializers.FloatField(allow_null=True)
    
    # Percentiles
    p50_time = serializers.FloatField(allow_null=True)
    p95_time = serializers.FloatField(allow_null=True)
    p99_time = serializers.FloatField(allow_null=True)
    
    # Success metrics
    total_evaluations = serializers.IntegerField()
    success_rate = serializers.FloatField()


# ========== Provider Info Serializers ==========

class ProviderInfoSerializer(serializers.Serializer):
    """Serializer for provider information"""
    provider_id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    is_enabled = serializers.BooleanField()
    demo_mode = serializers.BooleanField()
    voices = VoiceListSerializer(many=True)


class AvailableProvidersSerializer(serializers.Serializer):
    """Serializer for available providers list"""
    providers = ProviderInfoSerializer(many=True)

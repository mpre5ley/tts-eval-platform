# Database models for TTS Evaluation Platform

from django.db import models
from django.utils import timezone
import uuid


class TTSProvider(models.Model):
    """Configuration for TTS service providers"""
    
    # Unique provider identifier (e.g., 'elevenlabs', 'google', 'azure', 'amazon')
    provider_id = models.CharField(max_length=50, unique=True)
    
    # Display name
    name = models.CharField(max_length=100)
    
    # Provider description
    description = models.TextField(blank=True)
    
    # Whether provider is enabled
    is_enabled = models.BooleanField(default=True)
    
    # API endpoint base URL
    api_base_url = models.URLField(blank=True)
    
    # Provider-specific configuration as JSON
    config = models.JSONField(default=dict, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'TTS Provider'
        verbose_name_plural = 'TTS Providers'

    def __str__(self):
        return f"{self.name} ({'enabled' if self.is_enabled else 'disabled'})"


class Voice(models.Model):
    """Available voices for each TTS provider"""
    
    # Link to provider
    provider = models.ForeignKey(TTSProvider, on_delete=models.CASCADE, related_name='voices')
    
    # Voice ID as used by the provider's API
    voice_id = models.CharField(max_length=100)
    
    # Display name
    name = models.CharField(max_length=100)
    
    # Voice language/locale (e.g., 'en-US', 'es-ES')
    language = models.CharField(max_length=20, default='en-US')
    
    # Voice gender
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('neutral', 'Neutral'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='neutral')
    
    # Voice description
    description = models.TextField(blank=True)
    
    # Whether voice is available
    is_available = models.BooleanField(default=True)
    
    # Voice-specific settings as JSON
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['provider', 'name']
        unique_together = ['provider', 'voice_id']

    def __str__(self):
        return f"{self.provider.name} - {self.name}"


class EvaluationSession(models.Model):
    """A session containing multiple TTS synthesis evaluations"""
    
    # Unique session identifier
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Session name/label
    name = models.CharField(max_length=200, blank=True)
    
    # Text that was synthesized
    text = models.TextField()
    
    # Session notes
    notes = models.TextField(blank=True)
    
    # Session status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def evaluation_count(self):
        return self.evaluations.count()
    
    @property
    def successful_evaluations(self):
        return self.evaluations.filter(success=True).count()


class TTSEvaluation(models.Model):
    """Individual TTS synthesis evaluation with detailed metrics"""
    
    # Link to session
    session = models.ForeignKey(EvaluationSession, on_delete=models.CASCADE, related_name='evaluations')
    
    # Link to provider
    provider = models.ForeignKey(TTSProvider, on_delete=models.CASCADE, related_name='evaluations')
    
    # Link to voice used
    voice = models.ForeignKey(Voice, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluations')
    
    # Voice ID string used (stored separately in case voice is deleted)
    voice_id_str = models.CharField(max_length=100)
    
    # Voice name for display (human-readable name)
    voice_name = models.CharField(max_length=255, blank=True)
    
    # Provider-specific model/engine used
    model_id = models.CharField(max_length=100, blank=True)
    
    # Whether synthesis succeeded
    success = models.BooleanField(default=False)
    
    # Error message if failed
    error_message = models.TextField(blank=True)
    
    # ========== LATENCY METRICS (in milliseconds) ==========
    
    # Time from request sent to first byte received
    time_to_first_byte = models.FloatField(null=True, blank=True, help_text='TTFB in milliseconds')
    
    # Time from request sent to first audio chunk ready for playback
    time_to_first_audio = models.FloatField(null=True, blank=True, help_text='TTFA in milliseconds')
    
    # Total time from request to complete audio received
    total_synthesis_time = models.FloatField(null=True, blank=True, help_text='Total synthesis time in milliseconds')
    
    # Network round-trip time
    network_latency = models.FloatField(null=True, blank=True, help_text='Network RTT in milliseconds')
    
    # ========== AUDIO METRICS ==========
    
    # Audio duration in seconds
    audio_duration = models.FloatField(null=True, blank=True, help_text='Audio duration in seconds')
    
    # Audio file size in bytes
    audio_size = models.IntegerField(null=True, blank=True, help_text='Audio file size in bytes')
    
    # Audio format (mp3, wav, ogg, etc.)
    audio_format = models.CharField(max_length=20, default='mp3')
    
    # Sample rate in Hz
    sample_rate = models.IntegerField(null=True, blank=True, help_text='Sample rate in Hz')
    
    # Bitrate in kbps
    bitrate = models.IntegerField(null=True, blank=True, help_text='Bitrate in kbps')
    
    # ========== STREAMING METRICS ==========
    
    # Whether streaming was used
    is_streaming = models.BooleanField(default=False)
    
    # Number of chunks received (for streaming)
    chunk_count = models.IntegerField(null=True, blank=True)
    
    # Average chunk size in bytes
    avg_chunk_size = models.FloatField(null=True, blank=True, help_text='Average chunk size in bytes')
    
    # Chunk timing data as JSON array
    chunk_timings = models.JSONField(default=list, blank=True, help_text='Array of chunk arrival times')
    
    # ========== PLAYBACK JITTER METRICS ==========
    
    # Playback jitter (variation in chunk delivery times) in milliseconds
    playback_jitter = models.FloatField(null=True, blank=True, help_text='Playback jitter in milliseconds')
    
    # Min inter-chunk delay
    min_chunk_delay = models.FloatField(null=True, blank=True, help_text='Min inter-chunk delay in ms')
    
    # Max inter-chunk delay
    max_chunk_delay = models.FloatField(null=True, blank=True, help_text='Max inter-chunk delay in ms')
    
    # Average inter-chunk delay
    avg_chunk_delay = models.FloatField(null=True, blank=True, help_text='Avg inter-chunk delay in ms')
    
    # ========== REQUEST/RESPONSE METADATA ==========
    
    # Request parameters as JSON
    request_params = models.JSONField(default=dict, blank=True)
    
    # Response headers as JSON
    response_headers = models.JSONField(default=dict, blank=True)
    
    # Character count of input text
    character_count = models.IntegerField(default=0)
    
    # Word count of input text
    word_count = models.IntegerField(default=0)
    
    # ========== COMPUTED METRICS ==========
    
    # Characters per second (synthesis speed)
    chars_per_second = models.FloatField(null=True, blank=True)
    
    # Real-time factor (audio_duration / synthesis_time)
    realtime_factor = models.FloatField(null=True, blank=True)
    
    # ========== AUDIO STORAGE ==========
    
    # Path to stored audio file (relative to media root)
    audio_file_path = models.CharField(max_length=500, blank=True)
    
    # Audio content as base64 (for smaller files, optional)
    audio_base64 = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.provider.name} - {self.voice_id} ({self.total_synthesis_time or 'N/A'}ms)"
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from raw measurements"""
        if self.total_synthesis_time and self.total_synthesis_time > 0:
            # Characters per second
            if self.character_count:
                self.chars_per_second = (self.character_count / self.total_synthesis_time) * 1000
            
            # Real-time factor
            if self.audio_duration:
                self.realtime_factor = self.audio_duration / (self.total_synthesis_time / 1000)
        
        # Calculate jitter from chunk timings
        if self.chunk_timings and len(self.chunk_timings) > 1:
            delays = []
            for i in range(1, len(self.chunk_timings)):
                delay = self.chunk_timings[i] - self.chunk_timings[i-1]
                delays.append(delay)
            
            if delays:
                self.min_chunk_delay = min(delays)
                self.max_chunk_delay = max(delays)
                self.avg_chunk_delay = sum(delays) / len(delays)
                
                # Jitter is the standard deviation of delays
                mean_delay = self.avg_chunk_delay
                variance = sum((d - mean_delay) ** 2 for d in delays) / len(delays)
                self.playback_jitter = variance ** 0.5


class BenchmarkRun(models.Model):
    """A benchmark run comparing multiple providers"""
    
    # Unique benchmark identifier
    benchmark_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Benchmark name
    name = models.CharField(max_length=200)
    
    # Description
    description = models.TextField(blank=True)
    
    # Test texts used
    test_texts = models.JSONField(default=list, help_text='Array of test texts')
    
    # Providers included
    providers = models.ManyToManyField(TTSProvider, related_name='benchmarks')
    
    # Number of iterations per test
    iterations = models.IntegerField(default=3)
    
    # Benchmark status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Aggregated results as JSON
    results_summary = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Benchmark: {self.name} ({self.status})"


class ProviderMetricsAggregate(models.Model):
    """Aggregated metrics for each provider (updated periodically)"""
    
    # Link to provider
    provider = models.OneToOneField(TTSProvider, on_delete=models.CASCADE, related_name='metrics_aggregate')
    
    # Total evaluations
    total_evaluations = models.IntegerField(default=0)
    
    # Successful evaluations
    successful_evaluations = models.IntegerField(default=0)
    
    # Success rate
    success_rate = models.FloatField(default=0.0)
    
    # Average metrics
    avg_time_to_first_byte = models.FloatField(null=True, blank=True)
    avg_time_to_first_audio = models.FloatField(null=True, blank=True)
    avg_total_synthesis_time = models.FloatField(null=True, blank=True)
    avg_playback_jitter = models.FloatField(null=True, blank=True)
    avg_realtime_factor = models.FloatField(null=True, blank=True)
    
    # Percentile metrics (P50, P95, P99)
    p50_synthesis_time = models.FloatField(null=True, blank=True)
    p95_synthesis_time = models.FloatField(null=True, blank=True)
    p99_synthesis_time = models.FloatField(null=True, blank=True)
    
    # Min/Max metrics
    min_synthesis_time = models.FloatField(null=True, blank=True)
    max_synthesis_time = models.FloatField(null=True, blank=True)
    
    # Last updated
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Provider Metrics Aggregate'
        verbose_name_plural = 'Provider Metrics Aggregates'

    def __str__(self):
        return f"Metrics for {self.provider.name}"


    

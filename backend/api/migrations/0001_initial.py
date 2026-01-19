# Generated migration for TTS Evaluation models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TTSProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider_id', models.CharField(help_text='Unique provider identifier (e.g., elevenlabs, google, azure)', max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('api_endpoint', models.URLField(blank=True)),
                ('supports_streaming', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('config', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Voice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voice_id', models.CharField(help_text='Provider-specific voice identifier', max_length=100)),
                ('name', models.CharField(max_length=100)),
                ('language', models.CharField(default='en-US', max_length=20)),
                ('gender', models.CharField(choices=[('male', 'Male'), ('female', 'Female'), ('neutral', 'Neutral')], default='neutral', max_length=10)),
                ('description', models.TextField(blank=True)),
                ('is_available', models.BooleanField(default=True)),
                ('settings', models.JSONField(blank=True, default=dict)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='voices', to='api.ttsprovider')),
            ],
            options={
                'ordering': ['provider', 'name'],
                'unique_together': {('provider', 'voice_id')},
            },
        ),
        migrations.CreateModel(
            name='EvaluationSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(blank=True, max_length=200)),
                ('text', models.TextField()),
                ('notes', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TTSEvaluation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('voice_id_str', models.CharField(max_length=100)),
                ('model_id', models.CharField(blank=True, max_length=100)),
                ('success', models.BooleanField(default=False)),
                ('error_message', models.TextField(blank=True)),
                ('time_to_first_byte', models.FloatField(blank=True, help_text='TTFB in milliseconds', null=True)),
                ('time_to_first_audio', models.FloatField(blank=True, help_text='TTFA in milliseconds', null=True)),
                ('total_synthesis_time', models.FloatField(blank=True, help_text='Total synthesis time in milliseconds', null=True)),
                ('network_latency', models.FloatField(blank=True, help_text='Network RTT in milliseconds', null=True)),
                ('audio_duration', models.FloatField(blank=True, help_text='Audio duration in seconds', null=True)),
                ('audio_size', models.IntegerField(blank=True, help_text='Audio file size in bytes', null=True)),
                ('audio_format', models.CharField(default='mp3', max_length=20)),
                ('sample_rate', models.IntegerField(blank=True, help_text='Sample rate in Hz', null=True)),
                ('bitrate', models.IntegerField(blank=True, help_text='Bitrate in kbps', null=True)),
                ('is_streaming', models.BooleanField(default=False)),
                ('chunk_count', models.IntegerField(blank=True, help_text='Number of streaming chunks', null=True)),
                ('avg_chunk_size', models.FloatField(blank=True, help_text='Average chunk size in bytes', null=True)),
                ('chunk_timings', models.JSONField(blank=True, default=list, help_text='Array of chunk arrival times')),
                ('playback_jitter', models.FloatField(blank=True, help_text='Playback jitter in milliseconds', null=True)),
                ('min_chunk_delay', models.FloatField(blank=True, help_text='Minimum inter-chunk delay in ms', null=True)),
                ('max_chunk_delay', models.FloatField(blank=True, help_text='Maximum inter-chunk delay in ms', null=True)),
                ('avg_chunk_delay', models.FloatField(blank=True, help_text='Average inter-chunk delay in ms', null=True)),
                ('request_params', models.JSONField(blank=True, default=dict)),
                ('response_headers', models.JSONField(blank=True, default=dict)),
                ('character_count', models.IntegerField(blank=True, null=True)),
                ('word_count', models.IntegerField(blank=True, null=True)),
                ('chars_per_second', models.FloatField(blank=True, null=True)),
                ('realtime_factor', models.FloatField(blank=True, help_text='Audio duration / synthesis time', null=True)),
                ('audio_file_path', models.CharField(blank=True, max_length=500)),
                ('audio_base64', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='api.ttsprovider')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='api.evaluationsession')),
                ('voice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evaluations', to='api.voice')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BenchmarkRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('benchmark_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('test_texts', models.JSONField(default=list)),
                ('config', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('results_summary', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('sessions', models.ManyToManyField(blank=True, related_name='benchmarks', to='api.evaluationsession')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProviderMetricsAggregate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start', models.DateTimeField()),
                ('period_end', models.DateTimeField()),
                ('evaluation_count', models.IntegerField(default=0)),
                ('success_count', models.IntegerField(default=0)),
                ('failure_count', models.IntegerField(default=0)),
                ('avg_ttfb', models.FloatField(blank=True, null=True)),
                ('avg_ttfa', models.FloatField(blank=True, null=True)),
                ('avg_total_time', models.FloatField(blank=True, null=True)),
                ('avg_jitter', models.FloatField(blank=True, null=True)),
                ('p50_ttfa', models.FloatField(blank=True, null=True)),
                ('p95_ttfa', models.FloatField(blank=True, null=True)),
                ('p99_ttfa', models.FloatField(blank=True, null=True)),
                ('p50_total_time', models.FloatField(blank=True, null=True)),
                ('p95_total_time', models.FloatField(blank=True, null=True)),
                ('p99_total_time', models.FloatField(blank=True, null=True)),
                ('min_ttfa', models.FloatField(blank=True, null=True)),
                ('max_ttfa', models.FloatField(blank=True, null=True)),
                ('min_total_time', models.FloatField(blank=True, null=True)),
                ('max_total_time', models.FloatField(blank=True, null=True)),
                ('total_characters', models.BigIntegerField(default=0)),
                ('total_audio_duration', models.FloatField(default=0)),
                ('avg_realtime_factor', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='metrics_aggregates', to='api.ttsprovider')),
            ],
            options={
                'ordering': ['-period_start'],
                'unique_together': {('provider', 'period_start', 'period_end')},
            },
        ),
    ]

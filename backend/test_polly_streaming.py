#!/usr/bin/env python
"""Test Amazon Polly streaming implementation"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from api.services import AmazonPollyProvider
import statistics

provider = AmazonPollyProvider()
result = provider.synthesize_streaming(
    text='This is a test of the Amazon Polly streaming latency measurement.',
    voice_id='Joanna'
)

print('=' * 60)
print('Amazon Polly Streaming Test')
print('=' * 60)
print(f'Success: {result.success}')

if result.success:
    print(f'TTFB: {result.metrics.time_to_first_byte:.2f}ms')
    print(f'TTFA: {result.metrics.time_to_first_audio:.2f}ms')
    print(f'Total: {result.metrics.total_synthesis_time:.2f}ms')
    print(f'Chunk count: {result.metrics.chunk_count}')
    print(f'Avg chunk size: {result.metrics.avg_chunk_size:.0f} bytes')
    print(f'Audio size: {result.metrics.audio_size} bytes')
    
    if result.metrics.audio_duration:
        print(f'Audio Duration: {result.metrics.audio_duration:.3f}s')
    
    if result.metrics.realtime_factor:
        print(f'RTF: {result.metrics.realtime_factor:.2f}')
    
    # Calculate jitter
    if len(result.metrics.chunk_timings) > 1:
        intervals = []
        for i in range(1, len(result.metrics.chunk_timings)):
            intervals.append(result.metrics.chunk_timings[i] - result.metrics.chunk_timings[i-1])
        
        if len(intervals) > 1:
            jitter = statistics.stdev(intervals)
            print(f'Jitter (calculated): {jitter:.2f}ms')
        
        print(f'Chunk timing range: {result.metrics.chunk_timings[0]:.2f}ms to {result.metrics.chunk_timings[-1]:.2f}ms')
        print(f'Chunk spread: {result.metrics.chunk_timings[-1] - result.metrics.chunk_timings[0]:.2f}ms')
else:
    print(f'Error: {result.error_message}')

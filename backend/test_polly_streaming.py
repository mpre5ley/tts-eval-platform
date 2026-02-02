#!/usr/bin/env python
"""
Test Amazon Polly streaming to analyze TTFB, TTFA, and Chunk Jitter accuracy.
Compares generative vs neural engine streaming characteristics.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

import time
import statistics
from api.services import AmazonPollyProvider

def test_engine(provider, text, voice_id, engine):
    """Test a specific engine and analyze metrics."""
    print(f"\n{'='*60}")
    print(f"Testing: {voice_id} with {engine} engine")
    print(f"Text: '{text[:50]}...' ({len(text)} chars)")
    print(f"{'='*60}")
    
    result = provider.synthesize_streaming(
        text=text,
        voice_id=voice_id,
        engine=engine
    )
    
    if not result.success:
        print(f"ERROR: {result.error_message}")
        return None
    
    m = result.metrics
    print(f"\n--- Core Metrics ---")
    print(f"TTFB: {m.time_to_first_byte:.2f} ms")
    print(f"TTFA: {m.time_to_first_audio:.2f} ms")
    print(f"TTFA - TTFB gap: {m.time_to_first_audio - m.time_to_first_byte:.2f} ms")
    print(f"Total Latency: {m.total_synthesis_time:.2f} ms")
    
    print(f"\n--- Audio Info ---")
    print(f"Audio Size: {m.audio_size:,} bytes")
    print(f"Audio Duration: {m.audio_duration:.3f} seconds" if m.audio_duration else "Audio Duration: N/A")
    print(f"RTF: {m.realtime_factor:.2f}x" if m.realtime_factor else "RTF: N/A")
    
    print(f"\n--- Chunk Analysis ---")
    print(f"Chunk count: {m.chunk_count}")
    print(f"Avg chunk size: {m.avg_chunk_size:.0f} bytes")
    
    # Analyze chunk timing patterns
    if len(m.chunk_timings) > 1:
        delays = []
        for i in range(1, len(m.chunk_timings)):
            delays.append(m.chunk_timings[i] - m.chunk_timings[i-1])
        
        min_delay = min(delays)
        max_delay = max(delays)
        avg_delay = statistics.mean(delays)
        jitter = statistics.stdev(delays) if len(delays) > 1 else 0.0
        
        print(f"\n--- Inter-Chunk Delays ---")
        print(f"Min delay:  {min_delay:.3f} ms")
        print(f"Max delay:  {max_delay:.3f} ms")
        print(f"Avg delay:  {avg_delay:.3f} ms")
        print(f"Jitter (stdev): {jitter:.3f} ms")
        print(f"Reported jitter: {m.playback_jitter:.3f} ms" if m.playback_jitter else "Reported jitter: N/A")
        
        # Show first 10 chunk timings
        print(f"\n--- First 10 Chunk Arrivals ---")
        for i, t in enumerate(m.chunk_timings[:10]):
            delay_str = f"(+{delays[i-1]:.3f}ms)" if i > 0 else "(first)"
            print(f"  Chunk {i+1}: {t:.2f} ms {delay_str}")
        
        if len(m.chunk_timings) > 10:
            print(f"  ... and {len(m.chunk_timings) - 10} more chunks")
        
        # Streaming behavior analysis
        print(f"\n--- Streaming Behavior Analysis ---")
        
        total_chunk_time = m.chunk_timings[-1] - m.chunk_timings[0]
        print(f"Time to read all chunks: {total_chunk_time:.2f} ms")
        
        if max_delay > 10:
            print("✓ Some delays > 10ms detected - possible real streaming")
        else:
            print("✗ All delays < 10ms - likely reading from local buffer (pre-generated)")
        
        if jitter > 5:
            print(f"✓ Jitter ({jitter:.2f}ms) suggests variable network/generation timing")
        else:
            print(f"✗ Low jitter ({jitter:.2f}ms) suggests local buffer reads")
        
        if m.time_to_first_audio - m.time_to_first_byte > 50:
            print(f"✓ TTFA-TTFB gap ({m.time_to_first_audio - m.time_to_first_byte:.0f}ms) suggests streaming startup")
        else:
            print(f"✗ TTFA ≈ TTFB suggests audio was pre-generated before streaming")
        
        return {
            'ttfb': m.time_to_first_byte,
            'ttfa': m.time_to_first_audio,
            'total_time': m.total_synthesis_time,
            'jitter': jitter,
            'audio_duration': m.audio_duration,
            'rtf': m.realtime_factor,
            'delays': delays,
        }
    
    return None


def main():
    provider = AmazonPollyProvider()
    
    # Test text - substantial for meaningful metrics
    test_text = """
    Hello, this is a test of Amazon Polly's text-to-speech capabilities. 
    We are measuring the time to first byte, time to first audio, and chunk jitter 
    to understand the streaming characteristics of different engine types.
    This text is intentionally longer to generate more audio data and provide
    better insight into the streaming behavior of the synthesis engine.
    """
    
    print("\n" + "="*60)
    print("AMAZON POLLY STREAMING METRICS TEST")
    print("="*60)
    
    # Get available voices and their engines
    voices = provider.get_voices()
    
    # Find voices that support generative
    generative_voices = [v for v in voices if 'generative' in v.get('supported_engines', [])]
    neural_voices = [v for v in voices if 'neural' in v.get('supported_engines', [])]
    
    print(f"\nFound {len(generative_voices)} voices with generative engine")
    print(f"Found {len(neural_voices)} voices with neural engine")
    
    # Test with Ruth (supports generative) if available, otherwise Joanna (neural)
    test_configs = []
    
    # Check for Ruth (generative)
    for v in voices:
        if v['voice_id'] == 'Ruth':
            engines = v.get('supported_engines', [])
            print(f"\nRuth supports: {engines}")
            if 'generative' in engines:
                test_configs.append(('Ruth', 'generative'))
            if 'neural' in engines:
                test_configs.append(('Ruth', 'neural'))
            break
    
    # Also test Joanna for comparison
    for v in voices:
        if v['voice_id'] == 'Joanna':
            engines = v.get('supported_engines', [])
            print(f"Joanna supports: {engines}")
            if 'neural' in engines:
                test_configs.append(('Joanna', 'neural'))
            break
    
    # If no specific voices found, use defaults
    if not test_configs:
        print("\nUsing default test configurations...")
        test_configs = [
            ('Ruth', 'generative'),
            ('Ruth', 'neural'),
            ('Joanna', 'neural'),
        ]
    
    results = {}
    for voice_id, engine in test_configs:
        try:
            result = test_engine(provider, test_text, voice_id, engine)
            if result:
                results[(voice_id, engine)] = result
        except Exception as e:
            print(f"\nERROR testing {voice_id}/{engine}: {e}")
    
    # Summary comparison
    if len(results) > 1:
        print(f"\n{'='*60}")
        print("SUMMARY COMPARISON")
        print(f"{'='*60}")
        print(f"{'Voice':<12} {'Engine':<12} {'TTFB':>8} {'TTFA':>8} {'Total':>8} {'Jitter':>8} {'RTF':>6}")
        print("-" * 70)
        for (voice, engine), r in results.items():
            rtf_str = f"{r['rtf']:.2f}" if r['rtf'] else "N/A"
            print(f"{voice:<12} {engine:<12} {r['ttfb']:>7.0f}ms {r['ttfa']:>7.0f}ms {r['total_time']:>7.0f}ms {r['jitter']:>7.2f}ms {rtf_str:>6}")


if __name__ == '__main__':
    main()

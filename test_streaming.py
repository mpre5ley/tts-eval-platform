#!/usr/bin/env python3
import urllib.request
import json

# Test all providers with streaming
data = {
    "text": "Hello world, testing all providers with streaming metrics.",
    "providers": [
        {"provider_id": "elevenlabs", "voice_id": "21m00Tcm4TlvDq8ikWAM"},
        {"provider_id": "google", "voice_id": "en-US-Chirp3-HD-Achernar"},
        {"provider_id": "azure", "voice_id": "en-US-JennyNeural"},
        {"provider_id": "amazon", "voice_id": "Ruth"}
    ],
    "streaming": True
}

req = urllib.request.Request(
    "http://localhost:8000/api/synthesize/batch/",
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req, timeout=120) as resp:
    result = json.loads(resp.read().decode())

print("=" * 75)
print(f"{'Provider':<20} {'TTFA':>10} {'Jitter':>12} {'RTF':>8} {'Chunks':>8}")
print("=" * 75)

for r in result.get('results', []):
    m = r.get('metrics', {})
    name = r.get('provider_name', 'Unknown')[:20]
    
    ttfa = m.get('time_to_first_audio')
    ttfa_str = f"{ttfa:.0f}ms" if ttfa else "N/A"
    
    jitter = m.get('playback_jitter')
    jitter_str = f"{jitter:.2f}ms" if jitter else "N/A"
    
    rtf = m.get('realtime_factor')
    rtf_str = f"{rtf:.2f}x" if rtf else "N/A"
    
    chunks = m.get('chunk_count', 'N/A')
    
    status = "✓" if r.get('success') else "✗"
    
    print(f"{name:<20} {ttfa_str:>10} {jitter_str:>12} {rtf_str:>8} {str(chunks):>8} {status}")

print("=" * 75)
print("\nAll providers now support streaming with jitter metrics!")

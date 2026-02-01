#!/usr/bin/env python
"""Test ElevenLabs streaming to verify chunk timing"""
import os
import time
import requests
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('ELEVENLABS_API_KEY')
voice_id = 'EXAVITQu4vr4xnSDxMaL'  # Sarah voice

print('Testing ElevenLabs streaming...')
start_time = time.perf_counter() * 1000

response = requests.post(
    f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream',
    headers={
        'xi-api-key': api_key,
        'Content-Type': 'application/json',
        'Accept': 'audio/mpeg',
    },
    json={
        'text': 'Hello, this is a test of the streaming API. Let us see how the chunks arrive over time.',
        'model_id': 'eleven_multilingual_v2',
    },
    stream=True,
    timeout=60
)

headers_received = time.perf_counter() * 1000
print(f'HTTP headers received at: {headers_received - start_time:.1f} ms')
print(f'Status: {response.status_code}')

chunks = []
chunk_times = []
for i, chunk in enumerate(response.iter_content(chunk_size=1024)):
    if chunk:
        t = time.perf_counter() * 1000 - start_time
        chunk_times.append(t)
        chunks.append(chunk)
        if i < 10 or i % 20 == 0:
            print(f'  Chunk {i}: {len(chunk)} bytes at {t:.1f} ms')

end_time = time.perf_counter() * 1000
print(f'\nTotal chunks: {len(chunks)}')
print(f'Total size: {sum(len(c) for c in chunks)} bytes')
print(f'First chunk: {chunk_times[0]:.1f} ms')
print(f'Last chunk: {chunk_times[-1]:.1f} ms')
print(f'Total time: {end_time - start_time:.1f} ms')

# Show timing gaps
if len(chunk_times) > 1:
    gaps = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
    print(f'\nChunk gaps - Min: {min(gaps):.1f} ms, Max: {max(gaps):.1f} ms, Avg: {sum(gaps)/len(gaps):.1f} ms')

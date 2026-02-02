# TTS Service Providers - Interface with multiple TTS APIs and measure latency metrics

import os
import time
import base64
import statistics
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from io import BytesIO
from django.conf import settings
from django.utils import timezone
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()
backend_dir = Path(__file__).resolve().parent.parent


def get_audio_duration(audio_data: bytes, audio_format: str = 'mp3') -> Optional[float]:
    """
    Calculate audio duration in seconds from audio data.
    Uses pydub for accurate duration measurement.
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(BytesIO(audio_data), format=audio_format)
        return len(audio) / 1000.0  # pydub returns milliseconds
    except Exception as e:
        # Fallback: estimate from file size and typical bitrate
        # MP3 at 128kbps = 16KB per second
        # MP3 at 192kbps = 24KB per second
        try:
            if audio_format == 'mp3':
                # Assume ~128kbps average
                return len(audio_data) / 16000.0
            elif audio_format == 'wav':
                # Assume 16-bit mono 22050Hz = 44100 bytes per second
                return len(audio_data) / 44100.0
            elif audio_format == 'ogg':
                # Assume ~96kbps
                return len(audio_data) / 12000.0
        except:
            pass
        return None


@dataclass
class TTSMetrics:
    """Container for TTS synthesis metrics"""
    # Timing metrics (all in milliseconds)
    time_to_first_byte: Optional[float] = None
    time_to_first_audio: Optional[float] = None
    total_synthesis_time: Optional[float] = None
    network_latency: Optional[float] = None
    
    # Audio metrics
    audio_duration: Optional[float] = None  # seconds
    audio_size: Optional[int] = None  # bytes
    audio_format: str = 'mp3'
    sample_rate: Optional[int] = None
    bitrate: Optional[int] = None
    
    # Streaming metrics
    is_streaming: bool = False
    chunk_count: Optional[int] = None
    avg_chunk_size: Optional[float] = None
    chunk_timings: List[float] = field(default_factory=list)
    
    # Jitter metrics
    playback_jitter: Optional[float] = None
    min_chunk_delay: Optional[float] = None
    max_chunk_delay: Optional[float] = None
    avg_chunk_delay: Optional[float] = None
    
    # Request metadata
    character_count: int = 0
    word_count: int = 0
    
    # Computed metrics
    chars_per_second: Optional[float] = None
    realtime_factor: Optional[float] = None
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from raw measurements"""
        if self.total_synthesis_time and self.total_synthesis_time > 0:
            if self.character_count:
                self.chars_per_second = (self.character_count / self.total_synthesis_time) * 1000
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
                self.avg_chunk_delay = statistics.mean(delays)
                self.playback_jitter = statistics.stdev(delays) if len(delays) > 1 else 0.0


@dataclass
class TTSResult:
    """Result of a TTS synthesis operation"""
    success: bool
    audio_data: Optional[bytes] = None
    audio_base64: Optional[str] = None
    metrics: TTSMetrics = field(default_factory=TTSMetrics)
    error_message: str = ''
    provider_id: str = ''
    voice_id: str = ''
    model_id: str = ''
    response_headers: Dict[str, str] = field(default_factory=dict)


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    provider_id: str = ''
    provider_name: str = ''
    
    def __init__(self):
        self.api_key = None
        self.demo_mode = False
    
    @abstractmethod
    def synthesize(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text to speech"""
        pass
    
    @abstractmethod
    def synthesize_streaming(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text to speech with streaming"""
        pass
    
    @abstractmethod
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available voices for this provider"""
        pass
    
    def get_text_metrics(self, text: str) -> Tuple[int, int]:
        """Get character and word count for text"""
        char_count = len(text)
        word_count = len(text.split())
        return char_count, word_count
    
    def _generate_demo_audio(self, text: str) -> bytes:
        """Generate placeholder audio data for demo mode"""
        # Create a simple WAV header with silence
        # This is a minimal valid WAV file
        sample_rate = 22050
        duration = len(text) * 0.05  # ~50ms per character
        num_samples = int(sample_rate * duration)
        
        # WAV header
        wav_header = bytes([
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            0x24, 0x00, 0x00, 0x00,  # Chunk size (placeholder)
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            0x66, 0x6d, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # Subchunk1 size (16)
            0x01, 0x00,              # Audio format (PCM)
            0x01, 0x00,              # Num channels (1)
            0x22, 0x56, 0x00, 0x00,  # Sample rate (22050)
            0x44, 0xac, 0x00, 0x00,  # Byte rate
            0x02, 0x00,              # Block align
            0x10, 0x00,              # Bits per sample (16)
            0x64, 0x61, 0x74, 0x61,  # "data"
            0x00, 0x00, 0x00, 0x00,  # Subchunk2 size (placeholder)
        ])
        
        # Generate silence (zeros)
        audio_data = bytes(num_samples * 2)  # 16-bit samples
        
        return wav_header + audio_data


class ElevenLabsProvider(BaseTTSProvider):
    """ElevenLabs TTS API Provider"""
    
    provider_id = 'elevenlabs'
    provider_name = 'ElevenLabs'
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.demo_mode = not self.api_key
        self.base_url = 'https://api.elevenlabs.io/v1'
        
        if self.demo_mode:
            print('-----------------------------------------------------')
            print('ElevenLabs running in DEMO MODE - No API key found')
            print('Define ELEVENLABS_API_KEY in ./backend/.env')
            print('-----------------------------------------------------')
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available ElevenLabs voices"""
        if self.demo_mode:
            return settings.TTS_PROVIDERS.get('elevenlabs', {}).get('demo_voices', [])
        
        try:
            response = requests.get(
                f'{self.base_url}/voices',
                headers={'xi-api-key': self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        'voice_id': v['voice_id'],
                        'name': v['name'],
                        'language': v.get('labels', {}).get('language', 'en'),
                        'gender': v.get('labels', {}).get('gender', 'neutral'),
                        'description': v.get('description', ''),
                    }
                    for v in data.get('voices', [])
                ]
        except Exception as e:
            print(f"Error fetching ElevenLabs voices: {e}")
        
        return []
    
    def synthesize(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text using ElevenLabs API"""
        metrics = TTSMetrics()
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        model_id = kwargs.get('model_id', 'eleven_multilingual_v2')
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics, model_id)
        
        try:
            start_time = time.perf_counter() * 1000  # Convert to ms
            
            response = requests.post(
                f'{self.base_url}/text-to-speech/{voice_id}',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json',
                    'Accept': 'audio/mpeg',
                },
                json={
                    'text': text,
                    'model_id': model_id,
                    'voice_settings': kwargs.get('voice_settings', {
                        'stability': 0.5,
                        'similarity_boost': 0.75,
                    }),
                },
                timeout=60
            )
            
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if response.status_code == 200:
                audio_data = response.content
                end_time = time.perf_counter() * 1000
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.time_to_first_audio = metrics.time_to_first_byte
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model_id,
                    response_headers=dict(response.headers),
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message=f"API Error {response.status_code}: {response.text}",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model_id,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
                model_id=model_id,
            )
    
    def synthesize_streaming(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text using ElevenLabs streaming API"""
        metrics = TTSMetrics()
        metrics.is_streaming = True
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        model_id = kwargs.get('model_id', 'eleven_multilingual_v2')
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics, model_id)
        
        try:
            start_time = time.perf_counter() * 1000
            chunks = []
            chunk_sizes = []
            first_chunk_received = False
            
            response = requests.post(
                f'{self.base_url}/text-to-speech/{voice_id}/stream',
                headers={
                    'xi-api-key': self.api_key,
                    'Content-Type': 'application/json',
                    'Accept': 'audio/mpeg',
                },
                json={
                    'text': text,
                    'model_id': model_id,
                    'voice_settings': kwargs.get('voice_settings', {
                        'stability': 0.5,
                        'similarity_boost': 0.75,
                    }),
                },
                stream=True,
                timeout=60
            )
            
            # TTFB: Time when HTTP headers are received (before reading body)
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        current_time = time.perf_counter() * 1000
                        
                        if not first_chunk_received:
                            # TTFA: Time when first audio data is received
                            metrics.time_to_first_audio = current_time - start_time
                            first_chunk_received = True
                        
                        metrics.chunk_timings.append(current_time - start_time)
                        chunks.append(chunk)
                        chunk_sizes.append(len(chunk))
                
                end_time = time.perf_counter() * 1000
                audio_data = b''.join(chunks)
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                metrics.chunk_count = len(chunks)
                metrics.avg_chunk_size = statistics.mean(chunk_sizes) if chunk_sizes else 0
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model_id,
                    response_headers=dict(response.headers),
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message=f"Streaming API Error {response.status_code}: {response.text}",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model_id,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
                model_id=model_id,
            )
    
    def _demo_synthesis(self, text: str, voice_id: str, metrics: TTSMetrics, model_id: str) -> TTSResult:
        """Generate demo response with simulated metrics"""
        import random
        
        # Simulate realistic latency
        time.sleep(0.1 + random.random() * 0.2)
        
        metrics.time_to_first_byte = 50 + random.random() * 100
        metrics.time_to_first_audio = metrics.time_to_first_byte + 20 + random.random() * 50
        metrics.total_synthesis_time = metrics.time_to_first_audio + len(text) * (2 + random.random())
        metrics.audio_duration = len(text) * 0.06  # ~60ms per character
        metrics.audio_size = int(len(text) * 150)  # ~150 bytes per character
        metrics.audio_format = 'mp3'
        metrics.sample_rate = 44100
        metrics.calculate_derived_metrics()
        
        # Generate placeholder audio
        audio_data = self._generate_demo_audio(text)
        
        return TTSResult(
            success=True,
            audio_data=audio_data,
            audio_base64=base64.b64encode(audio_data).decode('utf-8'),
            metrics=metrics,
            provider_id=self.provider_id,
            voice_id=voice_id,
            model_id=model_id,
            error_message='DEMO MODE: Using simulated metrics',
        )


class GoogleTTSProvider(BaseTTSProvider):
    """Google Cloud Text-to-Speech Provider"""
    
    provider_id = 'google'
    provider_name = 'Google Cloud TTS'
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('GOOGLE_TTS_API_KEY')
        self.demo_mode = not self.api_key
        self.base_url = 'https://texttospeech.googleapis.com/v1'
        
        if self.demo_mode:
            print('-----------------------------------------------------')
            print('Google TTS running in DEMO MODE - No API key found')
            print('Define GOOGLE_TTS_API_KEY in ./backend/.env')
            print('-----------------------------------------------------')
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available Google TTS voices"""
        if self.demo_mode:
            return settings.TTS_PROVIDERS.get('google', {}).get('demo_voices', [])
        
        try:
            response = requests.get(
                f'{self.base_url}/voices',
                params={'key': self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        'voice_id': v['name'],
                        'name': v['name'],
                        'language': v['languageCodes'][0] if v.get('languageCodes') else 'en-US',
                        'gender': v.get('ssmlGender', 'NEUTRAL').lower(),
                        'description': f"{v['name']} - {v.get('ssmlGender', 'NEUTRAL')}",
                    }
                    for v in data.get('voices', [])
                ]
        except Exception as e:
            print(f"Error fetching Google TTS voices: {e}")
        
        return []
    
    def _get_full_voice_name(self, voice_id: str, language_code: str) -> str:
        """Get full voice name for Google TTS API.
        
        Newer Google TTS voices (star names like 'Achernar') need to be prefixed
        with the language and model, e.g., 'en-US-Chirp3-HD-Achernar'.
        Traditional voices (like 'en-US-Standard-A') work as-is.
        """
        # Traditional voices contain dashes and language codes
        if '-' in voice_id:
            return voice_id
        
        # Star name voices need the full format: {lang}-Chirp3-HD-{name}
        return f"{language_code}-Chirp3-HD-{voice_id}"
    
    def synthesize(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text using Google Cloud TTS API"""
        metrics = TTSMetrics()
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        language_code = kwargs.get('language_code', 'en-US')
        full_voice_name = self._get_full_voice_name(voice_id, language_code)
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics)
        
        try:
            start_time = time.perf_counter() * 1000
            
            response = requests.post(
                f'{self.base_url}/text:synthesize',
                params={'key': self.api_key},
                json={
                    'input': {'text': text},
                    'voice': {
                        'languageCode': language_code,
                        'name': full_voice_name,
                    },
                    'audioConfig': {
                        'audioEncoding': 'MP3',
                        'speakingRate': kwargs.get('speaking_rate', 1.0),
                        'pitch': kwargs.get('pitch', 0.0),
                    },
                },
                timeout=60
            )
            
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                audio_content = data.get('audioContent', '')
                audio_data = base64.b64decode(audio_content)
                
                end_time = time.perf_counter() * 1000
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.time_to_first_audio = metrics.time_to_first_byte
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=audio_content,
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    response_headers=dict(response.headers),
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message=f"API Error {response.status_code}: {response.text}",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
            )
    
    def synthesize_streaming(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Google TTS doesn't support streaming, use regular synthesis"""
        return self.synthesize(text, voice_id, **kwargs)
    
    def _demo_synthesis(self, text: str, voice_id: str, metrics: TTSMetrics) -> TTSResult:
        """Generate demo response with simulated metrics"""
        import random
        
        time.sleep(0.1 + random.random() * 0.2)
        
        metrics.time_to_first_byte = 60 + random.random() * 80
        metrics.time_to_first_audio = metrics.time_to_first_byte + 30 + random.random() * 40
        metrics.total_synthesis_time = metrics.time_to_first_audio + len(text) * (1.5 + random.random())
        metrics.audio_duration = len(text) * 0.055
        metrics.audio_size = int(len(text) * 140)
        metrics.audio_format = 'mp3'
        metrics.sample_rate = 24000
        metrics.calculate_derived_metrics()
        
        audio_data = self._generate_demo_audio(text)
        
        return TTSResult(
            success=True,
            audio_data=audio_data,
            audio_base64=base64.b64encode(audio_data).decode('utf-8'),
            metrics=metrics,
            provider_id=self.provider_id,
            voice_id=voice_id,
            error_message='DEMO MODE: Using simulated metrics',
        )


class AzureTTSProvider(BaseTTSProvider):
    """Azure Cognitive Services Text-to-Speech Provider"""
    
    provider_id = 'azure'
    provider_name = 'Azure TTS'
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('AZURE_TTS_API_KEY')
        self.region = os.getenv('AZURE_TTS_REGION', 'eastus')
        self.demo_mode = not self.api_key
        self.base_url = f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1'
        
        if self.demo_mode:
            print('-----------------------------------------------------')
            print('Azure TTS running in DEMO MODE - No API key found')
            print('Define AZURE_TTS_API_KEY in ./backend/.env')
            print('-----------------------------------------------------')
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available Azure TTS voices"""
        if self.demo_mode:
            return settings.TTS_PROVIDERS.get('azure', {}).get('demo_voices', [])
        
        try:
            response = requests.get(
                f'https://{self.region}.tts.speech.microsoft.com/cognitiveservices/voices/list',
                headers={'Ocp-Apim-Subscription-Key': self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                voices = response.json()
                return [
                    {
                        'voice_id': v['ShortName'],
                        'name': v['DisplayName'],
                        'language': v['Locale'],
                        'gender': v.get('Gender', 'Neutral').lower(),
                        'description': v.get('LocalName', ''),
                    }
                    for v in voices
                ]
        except Exception as e:
            print(f"Error fetching Azure TTS voices: {e}")
        
        return []
    
    def synthesize(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text using Azure TTS API"""
        metrics = TTSMetrics()
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics)
        
        try:
            start_time = time.perf_counter() * 1000
            
            ssml = f'''<speak version='1.0' xml:lang='en-US'>
                <voice xml:lang='en-US' name='{voice_id}'>{text}</voice>
            </speak>'''
            
            response = requests.post(
                self.base_url,
                headers={
                    'Ocp-Apim-Subscription-Key': self.api_key,
                    'Content-Type': 'application/ssml+xml',
                    'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3',
                },
                data=ssml.encode('utf-8'),
                timeout=60
            )
            
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if response.status_code == 200:
                audio_data = response.content
                end_time = time.perf_counter() * 1000
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.time_to_first_audio = metrics.time_to_first_byte
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                metrics.sample_rate = 16000
                metrics.bitrate = 128
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    response_headers=dict(response.headers),
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message=f"API Error {response.status_code}: {response.text}",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
            )
    
    def synthesize_streaming(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Azure TTS streaming synthesis"""
        # Azure supports streaming but requires websocket connection
        # For simplicity, use regular synthesis
        return self.synthesize(text, voice_id, **kwargs)
    
    def _demo_synthesis(self, text: str, voice_id: str, metrics: TTSMetrics) -> TTSResult:
        """Generate demo response with simulated metrics"""
        import random
        
        time.sleep(0.1 + random.random() * 0.2)
        
        metrics.time_to_first_byte = 70 + random.random() * 90
        metrics.time_to_first_audio = metrics.time_to_first_byte + 25 + random.random() * 45
        metrics.total_synthesis_time = metrics.time_to_first_audio + len(text) * (1.8 + random.random())
        metrics.audio_duration = len(text) * 0.058
        metrics.audio_size = int(len(text) * 160)
        metrics.audio_format = 'mp3'
        metrics.sample_rate = 16000
        metrics.bitrate = 128
        metrics.calculate_derived_metrics()
        
        audio_data = self._generate_demo_audio(text)
        
        return TTSResult(
            success=True,
            audio_data=audio_data,
            audio_base64=base64.b64encode(audio_data).decode('utf-8'),
            metrics=metrics,
            provider_id=self.provider_id,
            voice_id=voice_id,
            error_message='DEMO MODE: Using simulated metrics',
        )


class AmazonPollyProvider(BaseTTSProvider):
    """Amazon Polly TTS Provider"""
    
    provider_id = 'amazon'
    provider_name = 'Amazon Polly'
    
    def __init__(self):
        super().__init__()
        self.access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.demo_mode = not (self.access_key and self.secret_key)
        
        if self.demo_mode:
            print('-----------------------------------------------------')
            print('Amazon Polly running in DEMO MODE - No credentials found')
            print('Define AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in ./backend/.env')
            print('-----------------------------------------------------')
            self.client = None
        else:
            try:
                import boto3
                self.client = boto3.client(
                    'polly',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
            except ImportError:
                print('boto3 not installed, Amazon Polly unavailable')
                self.demo_mode = True
                self.client = None
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available Amazon Polly voices that support the generative engine.
        
        Only voices with generative engine support are returned to ensure
        accurate streaming metrics (TTFB, TTFA, jitter).
        """
        if self.demo_mode:
            return settings.TTS_PROVIDERS.get('amazon', {}).get('demo_voices', [])
        
        try:
            response = self.client.describe_voices()
            # Only return voices that support the generative engine
            return [
                {
                    'voice_id': v['Id'],
                    'name': v['Name'],
                    'language': v['LanguageCode'],
                    'gender': v.get('Gender', 'Neutral').lower(),
                    'description': f"{v['Name']} - {v['LanguageName']}",
                    'supported_engines': v.get('SupportedEngines', ['standard']),
                }
                for v in response.get('Voices', [])
                if 'generative' in v.get('SupportedEngines', [])
            ]
        except Exception as e:
            print(f"Error fetching Amazon Polly voices: {e}")
        
        return []
    
    def _get_best_engine(self, voice_id: str) -> str:
        """Get the generative engine for accurate streaming metrics.
        
        Only generative engine provides true streaming with accurate TTFB, TTFA, 
        and jitter measurements. Other engines pre-generate audio before streaming.
        """
        # Always use generative for accurate streaming metrics
        return 'generative'
    
    def synthesize(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text using Amazon Polly"""
        metrics = TTSMetrics()
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        # Always use generative engine for accurate metrics
        engine = 'generative'
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics)
        
        try:
            start_time = time.perf_counter() * 1000
            
            response = self.client.synthesize_speech(
                Text=text,
                VoiceId=voice_id,
                OutputFormat='mp3',
                Engine=engine
            )
            
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if 'AudioStream' in response:
                audio_data = response['AudioStream'].read()
                end_time = time.perf_counter() * 1000
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.time_to_first_audio = metrics.time_to_first_byte
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message="No audio stream in response",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
            )
    
    def synthesize_streaming(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Amazon Polly streaming synthesis - reads audio in chunks for jitter measurement"""
        metrics = TTSMetrics()
        metrics.is_streaming = True
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        # Always use generative engine for accurate streaming metrics
        engine = 'generative'
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics)
        
        try:
            start_time = time.perf_counter() * 1000
            chunks = []
            chunk_sizes = []
            first_chunk_received = False
            
            response = self.client.synthesize_speech(
                Text=text,
                VoiceId=voice_id,
                OutputFormat='mp3',
                Engine=engine
            )
            
            # TTFB: Time when API response is received
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if 'AudioStream' in response:
                audio_stream = response['AudioStream']
                
                # Read the stream in chunks (similar to ElevenLabs streaming)
                chunk_size = 1024
                while True:
                    chunk = audio_stream.read(chunk_size)
                    if not chunk:
                        break
                    
                    current_time = time.perf_counter() * 1000
                    
                    if not first_chunk_received:
                        # TTFA: Time when first audio data is received
                        metrics.time_to_first_audio = current_time - start_time
                        first_chunk_received = True
                    
                    metrics.chunk_timings.append(current_time - start_time)
                    chunks.append(chunk)
                    chunk_sizes.append(len(chunk))
                
                end_time = time.perf_counter() * 1000
                audio_data = b''.join(chunks)
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                metrics.chunk_count = len(chunks)
                metrics.avg_chunk_size = statistics.mean(chunk_sizes) if chunk_sizes else 0
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message="No audio stream in response",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
            )

    def _demo_synthesis(self, text: str, voice_id: str, metrics: TTSMetrics) -> TTSResult:
        """Generate demo response with simulated metrics"""
        import random
        
        time.sleep(0.1 + random.random() * 0.2)
        
        metrics.time_to_first_byte = 55 + random.random() * 75
        metrics.time_to_first_audio = metrics.time_to_first_byte + 20 + random.random() * 35
        metrics.total_synthesis_time = metrics.time_to_first_audio + len(text) * (1.2 + random.random())
        metrics.audio_duration = len(text) * 0.052
        metrics.audio_size = int(len(text) * 130)
        metrics.audio_format = 'mp3'
        metrics.sample_rate = 22050
        metrics.calculate_derived_metrics()
        
        audio_data = self._generate_demo_audio(text)
        
        return TTSResult(
            success=True,
            audio_data=audio_data,
            audio_base64=base64.b64encode(audio_data).decode('utf-8'),
            metrics=metrics,
            provider_id=self.provider_id,
            voice_id=voice_id,
            error_message='DEMO MODE: Using simulated metrics',
        )


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS Provider"""
    
    provider_id = 'openai'
    provider_name = 'OpenAI TTS'
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.demo_mode = not self.api_key
        self.base_url = 'https://api.openai.com/v1/audio/speech'
        
        if self.demo_mode:
            print('-----------------------------------------------------')
            print('OpenAI TTS running in DEMO MODE - No API key found')
            print('Define OPENAI_API_KEY in ./backend/.env')
            print('-----------------------------------------------------')
    
    def get_voices(self) -> List[Dict[str, Any]]:
        """Get available OpenAI TTS voices"""
        # OpenAI has a fixed set of voices
        return settings.TTS_PROVIDERS.get('openai', {}).get('demo_voices', [])
    
    def synthesize(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """Synthesize text using OpenAI TTS API"""
        metrics = TTSMetrics()
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        model = kwargs.get('model', 'tts-1')
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics, model)
        
        try:
            start_time = time.perf_counter() * 1000
            
            response = requests.post(
                self.base_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'input': text,
                    'voice': voice_id,
                    'response_format': 'mp3',
                },
                timeout=60
            )
            
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if response.status_code == 200:
                audio_data = response.content
                end_time = time.perf_counter() * 1000
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.time_to_first_audio = metrics.time_to_first_byte
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model,
                    response_headers=dict(response.headers),
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message=f"API Error {response.status_code}: {response.text}",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
            )
    
    def synthesize_streaming(self, text: str, voice_id: str, **kwargs) -> TTSResult:
        """OpenAI TTS streaming synthesis"""
        metrics = TTSMetrics()
        metrics.is_streaming = True
        char_count, word_count = self.get_text_metrics(text)
        metrics.character_count = char_count
        metrics.word_count = word_count
        
        model = kwargs.get('model', 'tts-1')
        
        if self.demo_mode:
            return self._demo_synthesis(text, voice_id, metrics, model)
        
        try:
            start_time = time.perf_counter() * 1000
            chunks = []
            chunk_sizes = []
            first_chunk_received = False
            
            response = requests.post(
                self.base_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'input': text,
                    'voice': voice_id,
                    'response_format': 'mp3',
                },
                stream=True,
                timeout=60
            )
            
            # TTFB is when we get the HTTP response (headers received)
            ttfb_time = time.perf_counter() * 1000
            metrics.time_to_first_byte = ttfb_time - start_time
            
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        current_time = time.perf_counter() * 1000
                        
                        if not first_chunk_received:
                            # TTFA is when we get the first audio chunk
                            metrics.time_to_first_audio = current_time - start_time
                            first_chunk_received = True
                        
                        metrics.chunk_timings.append(current_time - start_time)
                        chunks.append(chunk)
                        chunk_sizes.append(len(chunk))
                
                end_time = time.perf_counter() * 1000
                audio_data = b''.join(chunks)
                
                metrics.total_synthesis_time = end_time - start_time
                metrics.audio_size = len(audio_data)
                metrics.audio_format = 'mp3'
                metrics.chunk_count = len(chunks)
                metrics.avg_chunk_size = statistics.mean(chunk_sizes) if chunk_sizes else 0
                
                # Calculate actual audio duration
                metrics.audio_duration = get_audio_duration(audio_data, 'mp3')
                
                metrics.calculate_derived_metrics()
                
                return TTSResult(
                    success=True,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode('utf-8'),
                    metrics=metrics,
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model,
                    response_headers=dict(response.headers),
                )
            else:
                return TTSResult(
                    success=False,
                    metrics=metrics,
                    error_message=f"Streaming API Error {response.status_code}: {response.text}",
                    provider_id=self.provider_id,
                    voice_id=voice_id,
                    model_id=model,
                )
        
        except Exception as e:
            return TTSResult(
                success=False,
                metrics=metrics,
                error_message=str(e),
                provider_id=self.provider_id,
                voice_id=voice_id,
            )
    
    def _demo_synthesis(self, text: str, voice_id: str, metrics: TTSMetrics, model: str) -> TTSResult:
        """Generate demo response with simulated metrics"""
        import random
        
        time.sleep(0.1 + random.random() * 0.2)
        
        metrics.time_to_first_byte = 80 + random.random() * 120
        metrics.time_to_first_audio = metrics.time_to_first_byte + 30 + random.random() * 60
        metrics.total_synthesis_time = metrics.time_to_first_audio + len(text) * (2.5 + random.random())
        metrics.audio_duration = len(text) * 0.065
        metrics.audio_size = int(len(text) * 170)
        metrics.audio_format = 'mp3'
        metrics.sample_rate = 24000
        metrics.calculate_derived_metrics()
        
        audio_data = self._generate_demo_audio(text)
        
        return TTSResult(
            success=True,
            audio_data=audio_data,
            audio_base64=base64.b64encode(audio_data).decode('utf-8'),
            metrics=metrics,
            provider_id=self.provider_id,
            voice_id=voice_id,
            model_id=model,
            error_message='DEMO MODE: Using simulated metrics',
        )


class TTSServiceManager:
    """Manager class for TTS service providers"""
    
    _providers: Dict[str, BaseTTSProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_id: str) -> Optional[BaseTTSProvider]:
        """Get a TTS provider by ID"""
        if provider_id not in cls._providers:
            provider_class = {
                'elevenlabs': ElevenLabsProvider,
                'google': GoogleTTSProvider,
                'azure': AzureTTSProvider,
                'amazon': AmazonPollyProvider,
                'openai': OpenAITTSProvider,
            }.get(provider_id)
            
            if provider_class:
                cls._providers[provider_id] = provider_class()
        
        return cls._providers.get(provider_id)
    
    @classmethod
    def get_all_providers(cls) -> List[BaseTTSProvider]:
        """Get all available TTS providers"""
        provider_ids = ['elevenlabs', 'google', 'azure', 'amazon', 'openai']
        return [cls.get_provider(pid) for pid in provider_ids if cls.get_provider(pid)]
    
    @classmethod
    def synthesize(cls, provider_id: str, text: str, voice_id: str, 
                   streaming: bool = False, **kwargs) -> TTSResult:
        """Synthesize text using specified provider"""
        provider = cls.get_provider(provider_id)
        if not provider:
            return TTSResult(
                success=False,
                error_message=f"Unknown provider: {provider_id}",
                provider_id=provider_id,
            )
        
        if streaming:
            return provider.synthesize_streaming(text, voice_id, **kwargs)
        return provider.synthesize(text, voice_id, **kwargs)
    
    @classmethod
    def synthesize_multiple(cls, text: str, provider_configs: List[Dict[str, Any]],
                           streaming: bool = False) -> List[TTSResult]:
        """Synthesize text using multiple providers"""
        results = []
        for config in provider_configs:
            provider_id = config.get('provider_id')
            voice_id = config.get('voice_id')
            kwargs = config.get('options', {})
            
            result = cls.synthesize(provider_id, text, voice_id, streaming, **kwargs)
            results.append(result)
        
        return results
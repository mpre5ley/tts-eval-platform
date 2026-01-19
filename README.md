# TTS Evaluation Platform

A comprehensive end-to-end platform for evaluating Text-to-Speech (TTS) services. Compare multiple providers including **ElevenLabs**, **Google Cloud TTS**, **Azure Cognitive Services**, **Amazon Polly**, and **OpenAI TTS** with precise latency measurements.

## Features

### Metrics Measured
- **Time to First Byte (TTFB)**: Network latency until first response byte
- **Time to First Audio (TTFA)**: Latency until playable audio is available
- **Total Synthesis Time**: Complete end-to-end processing duration
- **Playback Jitter**: Variation in audio chunk delivery timing (streaming mode)
- **Real-time Factor**: Audio duration / synthesis time
- **Audio Quality Metrics**: Duration, file size, sample rate, bitrate

### Supported TTS Providers
| Provider | Streaming | Demo Mode |
|----------|-----------|-----------|
| ElevenLabs | ✅ | ✅ |
| Google Cloud TTS | ❌ | ✅ |
| Azure Cognitive Services | ❌ | ✅ |
| Amazon Polly | ❌ | ✅ |
| OpenAI TTS | ✅ | ✅ |

### Platform Features
- **Batch Evaluation**: Compare up to 5 providers simultaneously
- **Streaming Mode**: Measure chunk-by-chunk delivery for jitter analysis
- **Session History**: Review past evaluations and results
- **Aggregated Metrics**: View averages, percentiles (P50, P95, P99), and success rates
- **Visual Comparisons**: Charts and graphs for easy analysis
- **Audio Playback**: Listen to synthesized audio directly in browser
- **Client-side Jitter**: Measure playback jitter in the browser

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                           │
├─────────────────────────┬───────────────────────────────────┤
│     Frontend (3000)     │        Backend (8000)             │
│  ┌───────────────────┐  │  ┌─────────────────────────────┐  │
│  │  Django Templates │  │  │    Django REST Framework    │  │
│  │  - Evaluation UI  │  │  │  ┌─────────────────────┐    │  │
│  │  - Sessions View  │──┼──│  │   TTS Services      │    │  │
│  │  - Metrics View   │  │  │  │  - ElevenLabs       │    │  │
│  │  - Audio Playback │  │  │  │  - Google TTS       │    │  │
│  └───────────────────┘  │  │  │  - Azure TTS        │    │  │
│  ┌───────────────────┐  │  │  │  - Amazon Polly     │    │  │
│  │   Static Assets   │  │  │  │  - OpenAI TTS       │    │  │
│  │  - CSS Styles     │  │  │  └─────────────────────┘    │  │
│  │  - JavaScript     │  │  │  ┌─────────────────────┐    │  │
│  └───────────────────┘  │  │  │   SQLite Database   │    │  │
│                         │  │  │  - Sessions         │    │  │
│                         │  │  │  - Evaluations      │    │  │
│                         │  │  │  - Metrics          │    │  │
│                         │  │  └─────────────────────┘    │  │
│                         │  └─────────────────────────────┘  │
└─────────────────────────┴───────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) API keys for TTS providers

### 1. Clone and Configure

```bash
# Navigate to project directory
cd speech-synthesis-eval-framework

# Create environment file from template
cp backend/.env.example backend/.env

# Edit .env and add your API keys (optional - demo mode works without keys)
nano backend/.env
```

### 2. Run with Docker Compose

```bash
# Build and start containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 3. Access the Platform

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/
- **Health Check**: http://localhost:8000/api/health/

## Local Development (Without Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver 8000
```

### Frontend Setup

```bash
cd frontend

# Create virtual environment (separate from backend)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable for backend URL
export BACKEND_API_URL=http://127.0.0.1:8000/api
export SECRET_KEY=dev-secret-key
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1

# Start development server
python manage.py runserver 3000
```

## API Endpoints

### Providers
- `GET /api/providers/` - List all TTS providers and voices
- `GET /api/providers/{provider_id}/voices/` - Get voices for a provider

### Synthesis
- `POST /api/synthesize/` - Single provider synthesis
- `POST /api/synthesize/batch/` - Multi-provider synthesis

### Evaluations
- `GET /api/sessions/` - List evaluation sessions
- `GET /api/sessions/{session_id}/` - Get session details
- `GET /api/evaluations/` - List evaluations

### Metrics
- `GET /api/metrics/provider/{provider_id}/` - Provider metrics
- `GET /api/metrics/comparison/` - Cross-provider comparison

### Benchmarks
- `POST /api/benchmarks/create/` - Create benchmark run
- `GET /api/benchmarks/` - List benchmarks
- `GET /api/benchmarks/{benchmark_id}/` - Get benchmark details

## Example API Usage

### Batch Synthesis Request

```bash
curl -X POST http://localhost:8000/api/synthesize/batch/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test of text to speech synthesis.",
    "providers": [
      {"provider_id": "elevenlabs", "voice_id": "EXAVITQu4vr4xnSDxMaL"},
      {"provider_id": "openai", "voice_id": "nova"},
      {"provider_id": "google", "voice_id": "en-US-Neural2-C"}
    ],
    "streaming": false,
    "session_name": "Quick comparison test"
  }'
```

### Response Example

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Hello, this is a test of text to speech synthesis.",
  "results": [
    {
      "success": true,
      "provider_id": "elevenlabs",
      "provider_name": "ElevenLabs",
      "voice_id": "EXAVITQu4vr4xnSDxMaL",
      "audio_base64": "...",
      "audio_format": "mp3",
      "metrics": {
        "time_to_first_byte": 85.2,
        "time_to_first_audio": 120.5,
        "total_synthesis_time": 450.3,
        "audio_duration": 2.45,
        "audio_size": 39200,
        "realtime_factor": 5.44,
        "playback_jitter": null
      }
    }
  ],
  "timestamp": "2024-01-18T10:30:00Z"
}
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ELEVENLABS_API_KEY` | ElevenLabs API key | No (demo mode) |
| `GOOGLE_TTS_API_KEY` | Google Cloud API key | No (demo mode) |
| `AZURE_TTS_API_KEY` | Azure subscription key | No (demo mode) |
| `AZURE_TTS_REGION` | Azure region (default: eastus) | No |
| `AWS_ACCESS_KEY_ID` | AWS access key | No (demo mode) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | No (demo mode) |
| `AWS_REGION` | AWS region (default: us-east-1) | No |
| `OPENAI_API_KEY` | OpenAI API key | No (demo mode) |

### Demo Mode

When no API key is provided for a provider, it runs in **demo mode**:
- Generates placeholder audio (silent WAV)
- Simulates realistic latency metrics
- Useful for testing the platform without API costs

## Project Structure

```
speech-synthesis-eval-framework/
├── docker-compose.yml          # Docker orchestration
├── README.md                   # This file
├── backend/
│   ├── Dockerfile             # Backend container config
│   ├── manage.py              # Django management script
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example           # Environment template
│   ├── api/
│   │   ├── models.py          # Database models
│   │   ├── services.py        # TTS provider integrations
│   │   ├── serializers.py     # API serializers
│   │   ├── views.py           # API endpoints
│   │   └── urls.py            # URL routing
│   └── core/
│       ├── settings.py        # Django settings
│       └── urls.py            # Root URL config
└── frontend/
    ├── Dockerfile             # Frontend container config
    ├── manage.py              # Django management script
    ├── requirements.txt       # Python dependencies
    ├── chat/
    │   ├── views.py           # Frontend views
    │   └── urls.py            # URL routing
    ├── static/
    │   ├── css/style.css      # Styles
    │   └── js/main.js         # JavaScript
    └── templates/
        └── chat/
            ├── index.html     # Main evaluation page
            ├── sessions.html  # Session history
            └── metrics.html   # Metrics dashboard
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

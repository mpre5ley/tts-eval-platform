# Settings for Django configuration

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from env
load_dotenv()

# Assign environment variables for Django
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = os.environ['DEBUG'].lower() == 'true'
ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')

# Define Django and 3rd party apps for core functionality
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api',
]

# Define middleware used to handle requests, security, auth
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Defines URLs
ROOT_URLCONF = 'core.urls'

# Defines HTML rendering for Django, enables UI
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Defines web interface for Django app
WSGI_APPLICATION = 'core.wsgi.application'

# Defines database used, SQLite used for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Defines Django password validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Define time zone settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Define primary key field , reduces warnings
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings to allow admin access through web browser
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# Defines frontend dev servers
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Allows any domain in Docker
CORS_ALLOW_ALL_ORIGINS = os.getenv('DOCKER_ENV', 'false').lower() == 'true'

# ========== TTS Provider Configuration ==========
TTS_PROVIDERS = {
    'elevenlabs': {
        'name': 'ElevenLabs',
        'description': 'High-quality AI voice synthesis with natural-sounding voices',
        'enabled': True,
        'api_base_url': 'https://api.elevenlabs.io/v1',
        'demo_voices': [
            {
                'voice_id': 'EXAVITQu4vr4xnSDxMaL',
                'name': 'Sarah',
                'language': 'en-US',
                'gender': 'female',
                'description': 'Young American female voice, conversational'
            },
            {
                'voice_id': '21m00Tcm4TlvDq8ikWAM',
                'name': 'Rachel',
                'language': 'en-US',
                'gender': 'female',
                'description': 'American female voice, calm and clear'
            },
            {
                'voice_id': 'AZnzlk1XvdvUeBnXmlld',
                'name': 'Domi',
                'language': 'en-US',
                'gender': 'female',
                'description': 'Strong American female voice'
            },
            {
                'voice_id': 'pNInz6obpgDQGcFmaJgB',
                'name': 'Adam',
                'language': 'en-US',
                'gender': 'male',
                'description': 'Deep American male voice'
            },
            {
                'voice_id': 'yoZ06aMxZJJ28mfd3POQ',
                'name': 'Sam',
                'language': 'en-US',
                'gender': 'male',
                'description': 'Young American male voice'
            },
        ],
        'models': [
            {'id': 'eleven_multilingual_v2', 'name': 'Multilingual v2'},
            {'id': 'eleven_monolingual_v1', 'name': 'English v1'},
            {'id': 'eleven_turbo_v2', 'name': 'Turbo v2 (Faster)'},
        ]
    },
    'google': {
        'name': 'Google Cloud TTS',
        'description': 'Google Cloud Text-to-Speech with WaveNet and Neural2 voices',
        'enabled': True,
        'api_base_url': 'https://texttospeech.googleapis.com/v1',
        'demo_voices': [
            {
                'voice_id': 'en-US-Neural2-A',
                'name': 'Neural2-A',
                'language': 'en-US',
                'gender': 'male',
                'description': 'US English Neural2 male voice'
            },
            {
                'voice_id': 'en-US-Neural2-C',
                'name': 'Neural2-C',
                'language': 'en-US',
                'gender': 'female',
                'description': 'US English Neural2 female voice'
            },
            {
                'voice_id': 'en-US-Wavenet-D',
                'name': 'Wavenet-D',
                'language': 'en-US',
                'gender': 'male',
                'description': 'US English WaveNet male voice'
            },
            {
                'voice_id': 'en-US-Wavenet-F',
                'name': 'Wavenet-F',
                'language': 'en-US',
                'gender': 'female',
                'description': 'US English WaveNet female voice'
            },
            {
                'voice_id': 'en-GB-Neural2-A',
                'name': 'Neural2-A (UK)',
                'language': 'en-GB',
                'gender': 'female',
                'description': 'UK English Neural2 female voice'
            },
        ]
    },
    'azure': {
        'name': 'Azure TTS',
        'description': 'Microsoft Azure Cognitive Services Text-to-Speech',
        'enabled': True,
        'demo_voices': [
            {
                'voice_id': 'en-US-JennyNeural',
                'name': 'Jenny',
                'language': 'en-US',
                'gender': 'female',
                'description': 'US English Neural female voice'
            },
            {
                'voice_id': 'en-US-GuyNeural',
                'name': 'Guy',
                'language': 'en-US',
                'gender': 'male',
                'description': 'US English Neural male voice'
            },
            {
                'voice_id': 'en-US-AriaNeural',
                'name': 'Aria',
                'language': 'en-US',
                'gender': 'female',
                'description': 'US English Neural female voice, expressive'
            },
            {
                'voice_id': 'en-GB-SoniaNeural',
                'name': 'Sonia',
                'language': 'en-GB',
                'gender': 'female',
                'description': 'UK English Neural female voice'
            },
            {
                'voice_id': 'en-GB-RyanNeural',
                'name': 'Ryan',
                'language': 'en-GB',
                'gender': 'male',
                'description': 'UK English Neural male voice'
            },
        ]
    },
    'amazon': {
        'name': 'Amazon Polly',
        'description': 'Amazon Polly with Neural and Standard voices',
        'enabled': True,
        'demo_voices': [
            {
                'voice_id': 'Joanna',
                'name': 'Joanna',
                'language': 'en-US',
                'gender': 'female',
                'description': 'US English Neural female voice'
            },
            {
                'voice_id': 'Matthew',
                'name': 'Matthew',
                'language': 'en-US',
                'gender': 'male',
                'description': 'US English Neural male voice'
            },
            {
                'voice_id': 'Salli',
                'name': 'Salli',
                'language': 'en-US',
                'gender': 'female',
                'description': 'US English Neural female voice'
            },
            {
                'voice_id': 'Amy',
                'name': 'Amy',
                'language': 'en-GB',
                'gender': 'female',
                'description': 'UK English Neural female voice'
            },
            {
                'voice_id': 'Brian',
                'name': 'Brian',
                'language': 'en-GB',
                'gender': 'male',
                'description': 'UK English Neural male voice'
            },
        ]
    },
    'openai': {
        'name': 'OpenAI TTS',
        'description': 'OpenAI Text-to-Speech with high-quality voices',
        'enabled': True,
        'api_base_url': 'https://api.openai.com/v1/audio/speech',
        'demo_voices': [
            {
                'voice_id': 'alloy',
                'name': 'Alloy',
                'language': 'en-US',
                'gender': 'neutral',
                'description': 'Versatile, balanced voice'
            },
            {
                'voice_id': 'echo',
                'name': 'Echo',
                'language': 'en-US',
                'gender': 'male',
                'description': 'Warm, natural male voice'
            },
            {
                'voice_id': 'fable',
                'name': 'Fable',
                'language': 'en-US',
                'gender': 'neutral',
                'description': 'Expressive, narrative voice'
            },
            {
                'voice_id': 'onyx',
                'name': 'Onyx',
                'language': 'en-US',
                'gender': 'male',
                'description': 'Deep, authoritative voice'
            },
            {
                'voice_id': 'nova',
                'name': 'Nova',
                'language': 'en-US',
                'gender': 'female',
                'description': 'Friendly, conversational voice'
            },
            {
                'voice_id': 'shimmer',
                'name': 'Shimmer',
                'language': 'en-US',
                'gender': 'female',
                'description': 'Clear, pleasant voice'
            },
        ],
        'models': [
            {'id': 'tts-1', 'name': 'TTS-1 (Standard)'},
            {'id': 'tts-1-hd', 'name': 'TTS-1-HD (High Quality)'},
        ]
    },
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/' 
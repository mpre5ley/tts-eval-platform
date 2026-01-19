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
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://127.0.0.1:8000/api')

# Define Django and 3rd party apps for core functionality
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'chat',
]

# Define middleware used to handle requests, security, auth
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

# Defines URLs
ROOT_URLCONF = 'core.urls'

# Defines HTML rendering for Django, enables UI
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

# Defines web interface for Django app
WSGI_APPLICATION = 'core.wsgi.application'

# Defines database, db needs to be defined in backend
DATABASES = {}

# Define time zone settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Define primary key field , reduces warnings
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

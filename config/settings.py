"""
Django settings for hannyHR.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'django-insecure-dev-only-change-me'),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    DB_ENGINE=(str, 'sqlite'),
    DB_NAME=(str, 'db.sqlite3'),
    POSTGRES_DB=(str, 'hannyhr'),
    POSTGRES_USER=(str, 'hannyhr'),
    POSTGRES_PASSWORD=(str, 'hannyhr'),
    POSTGRES_HOST=(str, 'localhost'),
    POSTGRES_PORT=(str, '5432'),
)
environ.Env.read_env(BASE_DIR / '.env', silent=True)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'employees',
    'leave',
    'hr',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': (
            'django.db.backends.postgresql'
            if env('DB_ENGINE') == 'postgres'
            else 'django.db.backends.sqlite3'
        ),
        'NAME': (
            env('POSTGRES_DB')
            if env('DB_ENGINE') == 'postgres'
            else BASE_DIR / env('DB_NAME')
        ),
        **(
            {
                'USER': env('POSTGRES_USER'),
                'PASSWORD': env('POSTGRES_PASSWORD'),
                'HOST': env('POSTGRES_HOST'),
                'PORT': env('POSTGRES_PORT'),
            }
            if env('DB_ENGINE') == 'postgres'
            else {'OPTIONS': {'timeout': 20}}
        ),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG
            else 'whitenoise.storage.CompressedStaticFilesStorage'
        ),
    },
}
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'admin:login'
LOGIN_REDIRECT_URL = 'leave:leave_type_list'
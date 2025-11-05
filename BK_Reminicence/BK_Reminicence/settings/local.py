from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_secret("DB NAME"),
        'USER': get_secret("DB USER"),
        'PASSWORD': get_secret("DB PASSWORD"),
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': f"-c search_path={get_secret('DB SCHEMA')},public"
        }
    }
}

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==================================================
# SPOTIFY API CONFIGURATION
# ==================================================

SPOTIFY_CLIENT_ID = get_secret("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = get_secret("SPOTIFY_CLIENT_SECRET")


SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:8000/api/spotify/callback'

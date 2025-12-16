from .base import *
import firebase_admin
from firebase_admin import credentials
import os

# Ruta del archivo de credenciales de Firebase
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_ACCOUNT_KEY_PATH = os.path.join(BASE_DIR, '../secret.json')

# Inicializar Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK inicializado.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Database - DESCOMENTADO
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

# ==================================================
# SPOTIFY API CONFIGURATION
# ==================================================

SPOTIFY_CLIENT_ID = get_secret("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = get_secret("SPOTIFY_CLIENT_SECRET")

SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:5173/callback'

BASE_URL = "https://api.spotify.com/v1/me/player"
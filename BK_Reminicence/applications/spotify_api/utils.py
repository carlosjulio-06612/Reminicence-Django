import requests
import base64
import pytz
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import SpotifyUserToken


def get_spotify_user_profile(access_token):
    try:
        response = requests.get(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error obteniendo perfil de Spotify: {e}")
        return None


def find_or_create_user_from_spotify(spotify_profile):
    email = spotify_profile.get('email')
    display_name = spotify_profile.get('display_name', '')
    if not email: raise ValueError("El perfil de Spotify no contiene email")
    user = User.objects.filter(email=email).first()
    if user: return user, False
    
    username = email
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{email.split('@')[0]}_{counter}"
        counter += 1
    
    user = User.objects.create_user(
        username=username, email=email,
        first_name=display_name.split()[0] if display_name else '',
        last_name=' '.join(display_name.split()[1:]) if len(display_name.split()) > 1 else ''
    )
    user.set_unusable_password()
    user.save()
    return user, True


def save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id):
    expires_at = timezone.now() + timedelta(seconds=expires_in)
    SpotifyUserToken.objects.update_or_create(
        user=user,
        defaults={
            'access_token': access_token, 'refresh_token': refresh_token,
            'expires_at': expires_at, 'scope': scope,
            'spotify_user_id': spotify_user_id,
        }
    )


def refresh_spotify_token(user):
    try:
        token_instance = SpotifyUserToken.objects.get(user=user)
    except SpotifyUserToken.DoesNotExist:
        return None

    auth_str = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'refresh_token', 'refresh_token': token_instance.refresh_token,
    }, headers={'Authorization': f'Basic {auth_b64}'})
    
    if response.status_code != 200: return None
        
    token_data = response.json()
    access_token = token_data['access_token']
    expires_in = token_data['expires_in']
    scope = token_data.get('scope', token_instance.scope)
    refresh_token = token_data.get('refresh_token', token_instance.refresh_token)
    save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, token_instance.spotify_user_id)
    return access_token


def get_user_spotify_token(user):
    try:
        token_instance = SpotifyUserToken.objects.get(user=user)
        
        expires_at = token_instance.expires_at
        
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, pytz.utc)
        
        if (expires_at - timezone.now()) < timedelta(minutes=5):
            print("Token de Spotify expirado o a punto de expirar, refrescando...")
            return refresh_spotify_token(user)
            
        return token_instance.access_token
    except SpotifyUserToken.DoesNotExist:
        return None
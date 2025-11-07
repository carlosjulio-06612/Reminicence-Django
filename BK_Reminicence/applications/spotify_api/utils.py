import requests
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import SpotifyUserToken


def get_spotify_user_profile(access_token):
    """
    Obtiene el perfil del usuario de Spotify usando el access_token.
    
    Returns:
        dict: Datos del perfil de Spotify o None si falla
        Ejemplo: {
            'id': 'spotify_user_123',
            'email': 'usuario@example.com',
            'display_name': 'Nombre Usuario'
        }
    """
    try:
        response = requests.get(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error obteniendo perfil de Spotify: {e}")
        return None


def find_or_create_user_from_spotify(spotify_profile):
    """
    Busca un usuario por email de Spotify. Si no existe, lo crea.
    
    Args:
        spotify_profile (dict): Datos del perfil de Spotify
        
    Returns:
        tuple: (User, created) - Usuario y si fue creado o ya existía
    """
    email = spotify_profile.get('email')
    spotify_id = spotify_profile.get('id')
    display_name = spotify_profile.get('display_name', '')
    
    if not email:
        raise ValueError("El perfil de Spotify no contiene email")
    
    # Buscar si ya existe un usuario con ese email
    user = User.objects.filter(email=email).first()
    
    if user:
        # Usuario ya existe (puede haber sido creado con login tradicional)
        return user, False
    else:
        # Crear nuevo usuario usando email como username
        # Si el email ya existe como username, agregar sufijo
        username = email
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{email.split('@')[0]}_{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=display_name.split()[0] if display_name else '',
            last_name=' '.join(display_name.split()[1:]) if len(display_name.split()) > 1 else ''
        )
        
        # Usuario creado via Spotify no tiene contraseña usable
        user.set_unusable_password()
        user.save()
        
        return user, True


def save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id):
    """
    Guarda o actualiza los tokens de Spotify para un usuario.
    
    Args:
        user: Usuario de Django
        access_token: Token de acceso de Spotify
        refresh_token: Token de refresco de Spotify
        expires_in: Segundos hasta que expire el token
        scope: Permisos otorgados
        spotify_user_id: ID único del usuario en Spotify
    """
    expires_at = timezone.now() + timedelta(seconds=expires_in)
    
    SpotifyUserToken.objects.update_or_create(
        user=user,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at,
            'scope': scope,
            'spotify_user_id': spotify_user_id,
        }
    )
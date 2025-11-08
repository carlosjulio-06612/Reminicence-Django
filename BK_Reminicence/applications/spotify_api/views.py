from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import login
import urllib
import requests
from .models import SpotifyUserToken
from .utils import get_spotify_user_profile, find_or_create_user_from_spotify, save_spotify_tokens


def spotify_login_view(request):
    """
    Inicia el flujo de autenticación con Spotify.
    Soporta login social y vinculación de cuentas existentes.
    """
    scope = (
        'user-read-private user-read-email '
        'playlist-read-private user-library-read '
        'user-top-read '
        'user-read-recently-played' 
    )
    
    # Guardar tipo de autenticación en sesión
    request.session['spotify_auth_type'] = 'link' if request.user.is_authenticated else 'social_login'
    
    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'scope': scope,
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


def spotify_callback_view(request):
    """
    Procesa el callback de Spotify después de la autorización.
    """
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        return redirect('users:login')

    # Intercambiar código por tokens
    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    })
    
    if response.status_code != 200:
        return redirect('users:login')
    
    token_data = response.json()
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    expires_in = token_data['expires_in']
    scope = token_data['scope']
    
    # Obtener perfil de Spotify
    spotify_profile = get_spotify_user_profile(access_token)
    
    if not spotify_profile:
        return redirect('users:login')
    
    spotify_user_id = spotify_profile['id']
    spotify_email = spotify_profile.get('email')
    
    # Determinar tipo de autenticación
    auth_type = request.session.get('spotify_auth_type', 'link')
    
    if auth_type == 'social_login':
        # Login Social - Usuario no está autenticado
        from django.contrib.auth.models import User
        
        existing_user = User.objects.filter(email=spotify_email).first()
        
        if existing_user and existing_user.has_usable_password():
            # Email existe con contraseña - requiere confirmación
            request.session['pending_spotify_tokens'] = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'scope': scope,
                'spotify_user_id': spotify_user_id,
            }
            request.session['spotify_email_conflict'] = spotify_email
            return redirect('/accounts/link-spotify/')
        
        # Crear/obtener usuario y loguear
        user, created = find_or_create_user_from_spotify(spotify_profile)
        save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
    else:
        # Vinculación - Usuario ya está autenticado
        save_spotify_tokens(request.user, access_token, refresh_token, expires_in, scope, spotify_user_id)
    
    # Limpiar sesión
    request.session.pop('spotify_auth_type', None)
    
    return redirect('core:index')
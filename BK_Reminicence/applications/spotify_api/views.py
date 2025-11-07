from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.utils import timezone
from datetime import timedelta
import urllib
import requests
from .models import SpotifyUserToken
from .utils import get_spotify_user_profile, find_or_create_user_from_spotify, save_spotify_tokens


def spotify_login_view(request):
    """
    Redirige al usuario a la página de autorización de Spotify.
    
    Esta vista maneja DOS casos:
    1. Login Social: Usuario NO está autenticado → Se creará cuenta con Spotify
    2. Vinculación: Usuario YA está autenticado → Solo vincula Spotify a cuenta existente
    """
    scope = 'user-read-private user-read-email playlist-read-private user-library-read'
    
    # Guardar en sesión qué tipo de autenticación es
    if request.user.is_authenticated:
        request.session['spotify_auth_type'] = 'link'
    else:
        request.session['spotify_auth_type'] = 'social_login'
    
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
    Maneja el callback de Spotify después de la autorización.
    
    Flujo:
    1. Recibe código de autorización
    2. Intercambia código por tokens
    3. Obtiene perfil del usuario de Spotify
    4. Dependiendo del tipo de auth:
       - Social Login: Crea/busca usuario y lo loguea
       - Link: Vincula tokens a usuario actual
    """
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        # Usuario canceló la autorización o hubo error
        return redirect('/accounts/login/')

    # Canjea el código por tokens
    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    })
    
    if response.status_code != 200:
        # Error al obtener tokens
        return redirect('/accounts/login/')
    
    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in')
    scope = token_data.get('scope')
    
    # Obtener perfil del usuario de Spotify
    spotify_profile = get_spotify_user_profile(access_token)
    
    if not spotify_profile:
        # Error al obtener perfil
        return redirect('/accounts/login/')
    
    spotify_user_id = spotify_profile.get('id')
    spotify_email = spotify_profile.get('email')
    
    # Determinar qué tipo de autenticación es
    auth_type = request.session.get('spotify_auth_type', 'link')
    
    if auth_type == 'social_login':
        # CASO 1: Login Social - Usuario NO estaba autenticado
        
        # Verificar si el email ya existe en el sistema
        from django.contrib.auth.models import User
        existing_user = User.objects.filter(email=spotify_email).first()
        
        if existing_user and existing_user.has_usable_password():
            # El email ya existe Y tiene contraseña tradicional
            # Por seguridad, NO lo logueamos automáticamente
            # Lo redirigimos a una página de vinculación segura
            request.session['pending_spotify_tokens'] = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'scope': scope,
                'spotify_user_id': spotify_user_id,
            }
            request.session['spotify_email_conflict'] = spotify_email
            return redirect('/accounts/link-spotify/')
        
        # Si no existe o no tiene contraseña, crear/obtener usuario y loguear
        user, created = find_or_create_user_from_spotify(spotify_profile)
        
        # Guardar tokens
        save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id)
        
        # Loguear al usuario automáticamente
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
    else:
        # CASO 2: Vinculación - Usuario YA está autenticado
        user = request.user
        
        # Simplemente guardar/actualizar tokens para el usuario actual
        save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id)
    
    # Limpiar sesión
    if 'spotify_auth_type' in request.session:
        del request.session['spotify_auth_type']
    
    # Redirigir al dashboard
    return redirect('/')
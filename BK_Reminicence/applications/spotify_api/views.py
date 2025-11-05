from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import urllib
import requests
from .models import SpotifyUserToken

# Create your views here.


@login_required
def spotify_login_view(request):
    """
    Redirige al usuario a la página de autorización de Spotify.
    """
    scope = 'user-read-private user-read-email playlist-read-private user-library-read'
    
    params = {
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'scope': scope,
    }
    
    auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    
    return redirect(auth_url)


@login_required
def spotify_callback_view(request):
    """
    Maneja el callback de Spotify después de la autorización.
    """
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error:
        # Puedes manejar el error de forma más elegante (ej. mostrar un mensaje)
        return redirect('/') 

    # Canjea el código por un access token y un refresh token
    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    }).json()

    access_token = response.get('access_token')
    refresh_token = response.get('refresh_token')
    expires_in = response.get('expires_in')
    scope = response.get('scope')
    
    expires_at = timezone.now() + timedelta(seconds=expires_in)

    # Guarda o actualiza los tokens para el usuario actual
    SpotifyUserToken.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at,
            'scope': scope,
        }
    )

    # Redirige al usuario de vuelta al dashboard principal
    return redirect('/')
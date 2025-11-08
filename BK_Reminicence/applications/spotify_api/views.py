# applications/spotify_api/views.py

from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt  # 🎯 IMPORTANTE
import urllib
import requests
from .models import SpotifyUserToken
from applications.core.spotify_service import *
from applications.users.forms import *
from .utils import get_spotify_user_profile, find_or_create_user_from_spotify, save_spotify_tokens, get_user_spotify_token

def spotify_login_view(request):
    """
    Inicia el flujo de autenticación con Spotify.
    """
    scope = (
        'user-read-private user-read-email '
        'playlist-read-private user-library-read '
        'user-top-read '
        'user-read-recently-played '
        'user-read-playback-state '
        'user-modify-playback-state' 
    )
    
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
    
    spotify_profile = get_spotify_user_profile(access_token)
    
    if not spotify_profile:
        return redirect('users:login')
    
    spotify_user_id = spotify_profile['id']
    auth_type = request.session.get('spotify_auth_type', 'link')
    
    if auth_type == 'social_login':
        user, created = find_or_create_user_from_spotify(spotify_profile)
        save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    else:
        save_spotify_tokens(request.user, access_token, refresh_token, expires_in, scope, spotify_user_id)
    
    request.session.pop('spotify_auth_type', None)
    return redirect('core:index')

# ===================================================================
# ===== VISTAS PARA EL CONTROL DEL REPRODUCTOR =====================
# ===================================================================

BASE_URL = "https://api.spotify.com/v1/me/player"

@login_required
def get_current_playback(request):
    """Obtiene el estado actual de reproducción"""
    access_token = get_user_spotify_token(request.user)
    if not access_token:
        return JsonResponse({'error': 'No token'}, status=401)
        
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f"{BASE_URL}?additional_types=track,episode", headers=headers)

    if response.status_code == 200:
        return JsonResponse(response.json())
    if response.status_code == 204:
        return JsonResponse({'is_playing': False})
    return JsonResponse({'error': 'Failed to get playback state'}, status=response.status_code)


@login_required
@csrf_exempt  # 🎯 CRÍTICO: Deshabilita verificación CSRF para esta vista
@require_http_methods(["POST"])
def play_pause_playback(request):
    """Pausa o reanuda la reproducción"""
    access_token = get_user_spotify_token(request.user)
    if not access_token:
        return JsonResponse({'error': 'No token'}, status=401)
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Obtener is_playing desde POST o JSON
    is_playing_str = request.POST.get('is_playing', 'false')
    
    if not request.POST.get('is_playing'):
        try:
            import json
            data = json.loads(request.body.decode('utf-8'))
            is_playing_str = str(data.get('is_playing', 'false'))
        except:
            pass
    
    is_playing = is_playing_str.lower() == 'true'
    
    url = f"{BASE_URL}/{'pause' if is_playing else 'play'}"
    response = requests.put(url, headers=headers)
    
    if response.status_code == 204:
        return JsonResponse({'status': 'success', 'action': 'paused' if is_playing else 'playing'})
    
    return JsonResponse({'error': 'Failed to toggle playback'}, status=response.status_code)


@login_required
@csrf_exempt  # 🎯 CRÍTICO
@require_http_methods(["POST"])
def next_track_playback(request):
    """Salta a la siguiente canción"""
    access_token = get_user_spotify_token(request.user)
    if not access_token:
        return JsonResponse({'error': 'No token'}, status=401)
    
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.post(f"{BASE_URL}/next", headers=headers)
    
    if response.status_code == 204:
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Failed to skip to next'}, status=response.status_code)


@login_required
@csrf_exempt  # 🎯 CRÍTICO
@require_http_methods(["POST"])
def previous_track_playback(request):
    """Vuelve a la canción anterior"""
    access_token = get_user_spotify_token(request.user)
    if not access_token:
        return JsonResponse({'error': 'No token'}, status=401)
    
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.post(f"{BASE_URL}/previous", headers=headers)
    
    if response.status_code == 204:
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Failed to skip to previous'}, status=response.status_code)


@login_required
@csrf_exempt  # 🎯 CRÍTICO
@require_http_methods(["POST"])
def start_playback(request):
    """Inicia la reproducción de una canción/playlist/álbum específico"""
    access_token = get_user_spotify_token(request.user)
    if not access_token:
        return JsonResponse({'error': 'No token disponible'}, status=401)
    
    # Obtener URI desde POST o JSON
    uri = request.POST.get('uri')
    if not uri:
        try:
            import json
            data = json.loads(request.body.decode('utf-8'))
            uri = data.get('uri')
        except:
            pass
    
    if not uri:
        return JsonResponse({'error': 'URI no proporcionado'}, status=400)
    
    # Validar formato del URI
    if not uri.startswith('spotify:'):
        return JsonResponse({'error': 'URI inválido'}, status=400)
    
    url = f"{BASE_URL}/play"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Construir payload según el tipo de URI
    if uri.startswith('spotify:track:'):
        payload = {'uris': [uri]}
    elif uri.startswith('spotify:artist:'):
        payload = {'context_uri': uri}
    elif uri.startswith('spotify:album:'):
        payload = {'context_uri': uri}
    elif uri.startswith('spotify:playlist:'):
        payload = {'context_uri': uri}
    else:
        payload = {'uris': [uri]}
    
    print(f"[SPOTIFY] Reproduciendo: {uri}")
    print(f"[SPOTIFY] Payload: {payload}")
    
    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code == 204:
        print("[SPOTIFY] Reproducción iniciada exitosamente")
        return JsonResponse({'status': 'success'})
    
    # Manejar errores específicos
    error_details = {}
    if response.content:
        try:
            error_details = response.json()
        except:
            error_details = {'message': response.text}
    
    error_message = error_details.get('error', {}).get('message', 'Error desconocido')
    
    if response.status_code == 403:
        error_message = 'Se requiere Spotify Premium para usar esta función'
    elif response.status_code == 404:
        error_message = 'No se encontró ningún dispositivo activo. Abre Spotify en tu teléfono o computadora.'
    
    print(f"[SPOTIFY] Error {response.status_code}: {error_message}")
    
    return JsonResponse({
        'error': error_message,
        'details': error_details,
        'status_code': response.status_code
    }, status=response.status_code)
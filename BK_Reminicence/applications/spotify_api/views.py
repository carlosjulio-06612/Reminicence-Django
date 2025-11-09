import json
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import urllib
import requests
from .models import SpotifyUserToken
from applications.core.spotify_service import *
from applications.users.forms import *
from .utils import get_spotify_user_profile, find_or_create_user_from_spotify, save_spotify_tokens, get_user_spotify_token
from django.views.decorators.http import require_POST

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
        messages.error(request, 'Se canceló la autorización de Spotify.')
        return redirect('users:login')

    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
        'client_id': settings.SPOTIFY_CLIENT_ID,
        'client_secret': settings.SPOTIFY_CLIENT_SECRET,
    })
    
    if response.status_code != 200:
        messages.error(request, 'Error al obtener tokens de Spotify.')
        return redirect('users:login')
    
    token_data = response.json()
    access_token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    expires_in = token_data['expires_in']
    scope = token_data['scope']
    
    spotify_profile = get_spotify_user_profile(access_token)
    
    if not spotify_profile:
        messages.error(request, 'No se pudo obtener tu perfil de Spotify.')
        return redirect('users:login')
    
    spotify_user_id = spotify_profile['id']
    auth_type = request.session.get('spotify_auth_type', 'link')
    
    existing_token = SpotifyUserToken.objects.filter(spotify_user_id=spotify_user_id).first()
    
    if auth_type == 'social_login':
        # Login social: crear o encontrar usuario
        if existing_token:
            # Ya existe vinculación, hacer login con ese usuario
            user = existing_token.user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido de vuelta, {user.username}!')
        else:
            # No existe, crear nuevo usuario
            user, created = find_or_create_user_from_spotify(spotify_profile)
            save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            if created:
                messages.success(request, '¡Cuenta creada exitosamente con Spotify!')
            else:
                messages.success(request, 'Cuenta vinculada exitosamente con Spotify!')
    else:
        # Link manual: vincular a usuario ya autenticado
        if existing_token and existing_token.user != request.user:
            # La cuenta de Spotify ya está vinculada a OTRO usuario
            messages.error(
                request, 
                f'Esta cuenta de Spotify ya está vinculada al usuario "{existing_token.user.username}". '
                f'Primero desvincúlala desde ese usuario para poder vincularla aquí.',
                extra_tags='settings_page'
            )
            return redirect('users:settings')
        
        # Todo bien, vincular
        save_spotify_tokens(request.user, access_token, refresh_token, expires_in, scope, spotify_user_id)
        messages.success(request, 'Tu cuenta de Spotify ha sido vinculada exitosamente.', extra_tags='settings_page')
    
    request.session.pop('spotify_auth_type', None)
    return redirect('core:index')

# ===================================================================
# ===== VISTAS PARA EL CONTROL DEL REPRODUCTOR =====================
# ===================================================================

BASE_URL = "https://api.spotify.com/v1/me/player"

@login_required
def get_current_playback(request):
    """Obtiene el estado actual de reproducción usando el SpotifyService."""
    try:
        spotify_service = SpotifyService(request.user)

        # Si el servicio no se pudo inicializar (ej. no hay token), detenemos la ejecución.
        if not spotify_service.sp:
            return JsonResponse({'error': 'Spotify connection failed, token might be missing.'}, status=401)
        
        # Obtenemos el estado de reproducción desde el servicio
        current_playback = spotify_service.sp.current_playback()
        
        # Caso 1: Hay una canción reproduciéndose o en pausa en un dispositivo activo
        if current_playback and current_playback.get('item'):
            data = {
                'is_playing': current_playback['is_playing'],
                'progress_ms': current_playback['progress_ms'],
                'shuffle_state': current_playback.get('shuffle_state', False),
                'repeat_state': current_playback.get('repeat_state', 'off'),
                'item': {
                    'name': current_playback['item']['name'],
                    'duration_ms': current_playback['item']['duration_ms'],
                    'album': {
                        'images': current_playback['item']['album']['images']
                    },
                    'artists': [
                        {'name': artist['name']} 
                        for artist in current_playback['item']['artists']
                    ]
                }
            }
            return JsonResponse(data)
        # Devolvemos 'No Content' para que el frontend sepa que no hay nada que mostrar.
        else:
            return JsonResponse({}, status=204) # 204 No Content es el estándar

    except Exception as e:
        # Si algo sale mal (ej. la API de Spotify está caída), devolvemos un error.
        print(f"Error in get_current_playback: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
@csrf_exempt 
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
@csrf_exempt 
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
@csrf_exempt  
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
@csrf_exempt
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
    
@login_required
@require_POST # Asegura que esta vista solo acepte peticiones POST
def seek_in_track(request):
    """
    Salta a una posición específica en la canción que se está reproduciendo.
    """
    try:
        data = json.loads(request.body)
        position_ms = int(data.get('position_ms'))
        
        if position_ms is None:
            return JsonResponse({'status': 'error', 'message': 'position_ms no proporcionado'}, status=400)

        spotify_service = SpotifyService(request.user)
        if spotify_service.sp:
            spotify_service.sp.seek_track(position_ms)
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No se pudo conectar con Spotify'}, status=503)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
@require_POST
def shuffle_playback(request):
    """Activa o desactiva el modo aleatorio."""
    try:
        data = json.loads(request.body)
        shuffle_state = bool(data.get('state')) # Convertimos a booleano

        spotify_service = SpotifyService(request.user)
        if spotify_service.sp:
            spotify_service.sp.shuffle(shuffle_state)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'No se pudo conectar con Spotify'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def repeat_playback(request):
    """Cambia el modo de repetición: off -> context -> track."""
    try:
        data = json.loads(request.body)
        repeat_state = data.get('state') # Debe ser 'off', 'context', o 'track'

        if repeat_state not in ['off', 'context', 'track']:
            return JsonResponse({'status': 'error', 'message': 'Estado de repetición inválido'}, status=400)

        spotify_service = SpotifyService(request.user)
        if spotify_service.sp:
            spotify_service.sp.repeat(repeat_state)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'No se pudo conectar con Spotify'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
@require_POST
def play_spotify_uri(request):
    """
    Inicia la reproducción de una URI o una lista de URIs, usando el
    parámetro correcto de la API de Spotify (context_uri vs uris).
    """
    try:
        data = json.loads(request.body)
        uri_to_play = data.get('uri')
        context_uri = data.get('context_uri') # Para una canción dentro de una playlist/álbum
        uris_list = data.get('uris')           # Para la lista de top tracks de un artista

        if not uri_to_play and not uris_list:
            return JsonResponse({'status': 'error', 'message': 'URI(s) no proporcionada(s)'}, status=400)

        spotify_service = SpotifyService(request.user)
        if spotify_service.sp:
            # Caso 1: Se proporciona una lista de canciones (ej. top tracks de artista)
            if uris_list:
                spotify_service.sp.start_playback(uris=uris_list)
            
            # Caso 2: Se proporciona una canción específica DENTRO de un contexto (playlist/álbum)
            elif context_uri and 'track' in uri_to_play:
                spotify_service.sp.start_playback(context_uri=context_uri, offset={'uri': uri_to_play})
            
            # Caso 3: Se proporciona una única URI. Debemos decidir cómo reproducirla.
            elif uri_to_play:
                # Si es una canción, la reproducimos en una lista de un solo elemento
                if 'track' in uri_to_play:
                    spotify_service.sp.start_playback(uris=[uri_to_play])
                # ¡LA CORRECCIÓN CLAVE! Si es un álbum, playlist o artista, es el CONTEXTO.
                else:
                    spotify_service.sp.start_playback(context_uri=uri_to_play)
            
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'error', 'message': 'No se pudo conectar con Spotify'}, status=503)

    except Exception as e:
        # Imprimimos el error en la consola de Django para poder depurar
        print(f"Error en play_spotify_uri: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
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
from applications.core.spotify_service import SpotifyService
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
        'user-modify-playback-state '
        'streaming'  # IMPORTANTE: Necesario para Web Playback SDK
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
        if existing_token:
            user = existing_token.user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido de vuelta, {user.username}!')
        else:
            user, created = find_or_create_user_from_spotify(spotify_profile)
            save_spotify_tokens(user, access_token, refresh_token, expires_in, scope, spotify_user_id)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            if created:
                messages.success(request, '¡Cuenta creada exitosamente con Spotify!')
            else:
                messages.success(request, 'Cuenta vinculada exitosamente con Spotify!')
    else:
        if existing_token and existing_token.user != request.user:
            messages.error(
                request, 
                f'Esta cuenta de Spotify ya está vinculada al usuario "{existing_token.user.username}". '
                f'Primero desvincúlala desde ese usuario para poder vincularla aquí.',
                extra_tags='settings_page'
            )
            return redirect('users:settings')
        
        save_spotify_tokens(request.user, access_token, refresh_token, expires_in, scope, spotify_user_id)
        messages.success(request, 'Tu cuenta de Spotify ha sido vinculada exitosamente.', extra_tags='settings_page')
    
    request.session.pop('spotify_auth_type', None)
    return redirect('core:index')

# ===================================================================
# ===== VISTAS PARA EL CONTROL DEL REPRODUCTOR =====================
# ===================================================================

@login_required
def get_current_playback(request):
    """Obtiene el estado actual de reproducción"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({}, status=401)
        
        current_playback = spotify_service.sp.current_playback()
        
        if current_playback and current_playback.get('item'):
            return JsonResponse({
                'is_playing': current_playback['is_playing'],
                'progress_ms': current_playback['progress_ms'],
                'shuffle_state': current_playback.get('shuffle_state', False),
                'repeat_state': current_playback.get('repeat_state', 'off'),
                'item': {
                    'name': current_playback['item']['name'],
                    'duration_ms': current_playback['item']['duration_ms'],
                    'album': {'images': current_playback['item']['album']['images']},
                    'artists': [{'name': a['name']} for a in current_playback['item']['artists']]
                }
            })
        else:
            return JsonResponse({}, status=204)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def play_spotify_uri(request):
    """Inicia la reproducción de una canción/playlist/álbum específico"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body) if request.body else {}
        device_id = data.get('device_id')
        uri_to_play = data.get('uri')
        context_uri = data.get('context_uri')
        uris_list = data.get('uris')

        if uris_list:
            spotify_service.sp.start_playback(uris=uris_list, device_id=device_id)
        elif context_uri:
            spotify_service.sp.start_playback(
                context_uri=context_uri, 
                offset={'uri': uri_to_play}, 
                device_id=device_id
            )
        elif uri_to_play:
            if 'track' in uri_to_play:
                spotify_service.sp.start_playback(uris=[uri_to_play], device_id=device_id)
            else:
                spotify_service.sp.start_playback(context_uri=uri_to_play, device_id=device_id)
        else:
            spotify_service.sp.start_playback(device_id=device_id)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def pause_playback(request):
    """Pausa la reproducción"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body) if request.body else {}
        spotify_service.sp.pause_playback(device_id=data.get('device_id'))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def next_track(request):
    """Salta a la siguiente canción"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body) if request.body else {}
        spotify_service.sp.next_track(device_id=data.get('device_id'))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def previous_track(request):
    """Vuelve a la canción anterior"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body) if request.body else {}
        spotify_service.sp.previous_track(device_id=data.get('device_id'))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def seek_in_track(request):
    """Salta a una posición específica en la canción"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body)
        position_ms = int(data.get('position_ms'))
        
        if position_ms is None:
            return JsonResponse({'error': 'position_ms no proporcionado'}, status=400)
        
        spotify_service.sp.seek_track(position_ms, device_id=data.get('device_id'))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def shuffle_playback(request):
    """Activa o desactiva el modo aleatorio"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body)
        shuffle_state = bool(data.get('state'))
        
        spotify_service.sp.shuffle(shuffle_state, device_id=data.get('device_id'))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def repeat_playback(request):
    """Cambia el modo de repetición: off -> context -> track"""
    try:
        spotify_service = SpotifyService(request.user)
        if not spotify_service.sp: 
            return JsonResponse({'error': 'Spotify connection failed'}, status=503)
        
        data = json.loads(request.body)
        repeat_state = data.get('state')
        
        if repeat_state not in ['off', 'context', 'track']:
            return JsonResponse({'error': 'Estado de repetición inválido'}, status=400)
        
        spotify_service.sp.repeat(repeat_state, device_id=data.get('device_id'))
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
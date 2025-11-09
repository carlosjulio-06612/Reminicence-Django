# core/views.py (ACTUALIZADO)

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .spotify_service import SpotifyService
from applications.spotify_api.models import SpotifyUserToken
from applications.music.models import Playlist, PlaybackHistory
from applications.music.sync_service import SpotifySyncService
from django.utils import timezone
from datetime import timedelta
from applications.music.models import Playlist, Songs, Artists

@login_required
def index(request):
    """Vista principal que muestra el dashboard de Spotify"""
    context = {
        'user_profile': None,
        'user_playlists': [],
        'top_tracks': [],
        'recently_played': [],
        'top_artists': [],
        'spotify_connected': False,
        'db_stats': {
            'playlists_count': 0,
            'songs_count': 0,
            'artists_count': 0, 
        }
    }
    
    try:
        spotify_token = SpotifyUserToken.objects.get(user=request.user)
        if spotify_token.access_token:
            context['spotify_connected'] = True
            context['db_stats']['playlists_count'] = Playlist.objects.filter(user=request.user).count()
            context['db_stats']['songs_count'] = Songs.objects.count()
            context['db_stats']['artists_count'] = Artists.objects.count()
            
            spotify_service = SpotifyService(request.user)
            
            if spotify_service.sp:
                context['user_profile'] = spotify_service.get_user_profile()
                context['user_playlists'] = spotify_service.get_user_playlists()
                context['top_tracks'] = spotify_service.get_user_top_tracks(limit=6)
                context['recently_played'] = spotify_service.get_recently_played(limit=6)
                context['top_artists'] = spotify_service.get_user_top_artists(limit=5)
                
    except SpotifyUserToken.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error en la vista index: {e}")
    
    # CORRECCIÓN: Si es una petición de HTMX, devuelve el parcial que incluye la top_bar.
    if request.headers.get('HX-Request'):
        return render(request, 'core/partials/_index_content.html', context)
    
    return render(request, 'core/index.html', context)


@login_required
def disconnect_spotify(request):
    try:
        spotify_token = SpotifyUserToken.objects.get(user=request.user)
        spotify_token.delete()
    except SpotifyUserToken.DoesNotExist:
        pass
    return redirect('core:index')


@login_required
def sync_spotify_data(request):
    try:
        sync_service = SpotifySyncService(request.user)
        results = sync_service.full_sync()
    except Exception as e:
        print(f"Error durante sincronización: {e}")
    return redirect('core:index')
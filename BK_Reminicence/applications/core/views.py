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
    
    # Verificar si el usuario tiene Spotify conectado
    try:
        spotify_token = SpotifyUserToken.objects.get(user=request.user)
        if spotify_token.access_token:
            context['spotify_connected'] = True
            # Contar playlists vinculadas a este usuario
            context['db_stats']['playlists_count'] = Playlist.objects.filter(user=request.user).count()
            # Contar TODAS las canciones y artistas en la base de datos
            context['db_stats']['songs_count'] = Songs.objects.count()
            context['db_stats']['artists_count'] = Artists.objects.count()
            
            # Inicializar servicio de Spotify
            spotify_service = SpotifyService(request.user)
            
            if spotify_service.sp:
                # Obtener datos de Spotify (para mostrar en tiempo real)
                context['user_playlists'] = spotify_service.get_user_playlists()
                context['top_tracks'] = spotify_service.get_user_top_tracks(limit=6)
                context['recently_played'] = spotify_service.get_recently_played(limit=6)
                context['top_artists'] = spotify_service.get_user_top_artists(limit=5)
                
    except SpotifyUserToken.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error en la vista index: {e}")
    
    return render(request, 'core/index.html', context)


@login_required
def disconnect_spotify(request):
    """Desconecta la cuenta de Spotify del usuario"""
    try:
        spotify_token = SpotifyUserToken.objects.get(user=request.user)
        spotify_token.delete()
    except SpotifyUserToken.DoesNotExist:
        pass
    
    return redirect('core:index')


@login_required
def sync_spotify_data(request):
    """Sincroniza los datos de Spotify del usuario con la base de datos"""
    try:
        sync_service = SpotifySyncService(request.user)
        results = sync_service.full_sync()
        
        
    except Exception as e:
        print(f"Error durante sincronización: {e}")
    
    return redirect('core:index')

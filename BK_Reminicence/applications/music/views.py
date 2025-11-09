from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Playlist
from applications.core.spotify_service import SpotifyService 


@login_required
def playlist_detail_view(request, playlist_id):
    """
    Muestra los detalles y las canciones de una playlist específica.
    """
    playlist = get_object_or_404(
        Playlist, 
        spotify_id=playlist_id, 
        user=request.user
    )
    
    songs_in_playlist = playlist.songs.all().select_related(
        'album', 
        'album__artist'
    ).order_by('playlistsong__position')
    
    for song in songs_in_playlist:
        if song.spotify_id:
            song.spotify_uri = f"spotify:track:{song.spotify_id}"
        else:
            song.spotify_uri = None 

    context = {
        'playlist': playlist,
        'songs': songs_in_playlist,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'music/partials/_playlist_detail_content.html', context)
    
    return render(request, 'music/playlist_detail.html', context)

@login_required
def artist_detail_view(request, artist_id):
    """
    Muestra los detalles, top tracks y álbumes de un artista específico.
    """
    context = {}
    try:
        spotify_service = SpotifyService(request.user)
        if spotify_service.sp:
            context['artist'] = spotify_service.get_artist_details(artist_id)
            context['top_tracks'] = spotify_service.get_artist_top_tracks(artist_id, limit=10)
            context['albums'] = spotify_service.get_artist_albums(artist_id)
    except Exception as e:
        print(f"Error en artist_detail_view: {e}")

    if request.headers.get('HX-Request'):
        return render(request, 'music/partials/_artist_detail_content.html', context)

    return render(request, 'music/artist_detail.html', context)

@login_required
def album_detail_view(request, album_id):
    """
    Muestra los detalles y las canciones de un álbum específico.
    """
    context = {}
    try:
        spotify_service = SpotifyService(request.user)
        if spotify_service.sp:
            # Esta función de servicio nos devolverá tanto los detalles del álbum como sus canciones
            album_data = spotify_service.get_album_details(album_id)
            if album_data:
                context['album'] = album_data['album_info']
                context['tracks'] = album_data['tracks']
    except Exception as e:
        print(f"Error en album_detail_view: {e}")

    # Lógica para HTMX
    if request.headers.get('HX-Request'):
        return render(request, 'music/partials/_album_detail_content.html', context)

    return render(request, 'music/album_detail.html', context)

@login_required
def search_view(request):
    """
    Maneja la búsqueda y devuelve un fragmento para HTMX o una página completa
    para navegación normal.
    """
    query = request.GET.get('q', '').strip()
    context = {'query': query, 'results': {}}

    if query:
        spotify_service = SpotifyService(request.user)
        search_results = spotify_service.search_spotify(query)
        context['results'] = search_results

    # --- LA CORRECCIÓN CLAVE ---
    if request.headers.get('HX-Request'):
        # Si la petición es de HTMX, devuelve solo el fragmento.
        return render(request, 'music/partials/_search_results.html', context)
    else:
        # Si es una carga normal, devuelve la página completa que tiene los CSS.
        return render(request, 'music/search.html', context)
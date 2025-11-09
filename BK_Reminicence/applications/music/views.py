from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Playlist

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
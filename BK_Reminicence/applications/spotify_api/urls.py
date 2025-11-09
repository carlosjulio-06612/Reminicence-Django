# applications/spotify_api/urls.py

from django.urls import path
from . import views

app_name = 'spotify_api'

urlpatterns = [
    # Autenticación
    path('login/', views.spotify_login_view, name='spotify_login'),
    path('callback/', views.spotify_callback_view, name='spotify_callback'),
    
    # Control del reproductor
    path('player/current/', views.get_current_playback, name='player_current'),
    path('player/play/', views.play_spotify_uri, name='play_spotify_uri'),
    path('player/pause/', views.pause_playback, name='pause_playback'),
    path('player/next/', views.next_track, name='next_track'),
    path('player/previous/', views.previous_track, name='previous_track'),
    path('player/seek/', views.seek_in_track, name='seek_track'),
    path('player/shuffle/', views.shuffle_playback, name='shuffle_playback'),
    path('player/repeat/', views.repeat_playback, name='repeat_playback'),
]
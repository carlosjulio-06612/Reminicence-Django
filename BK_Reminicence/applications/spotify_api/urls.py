# applications/spotify_api/urls.py

from django.urls import path
from . import views

app_name = 'spotify_api'

urlpatterns = [
    path('login/', views.spotify_login_view, name='spotify_login'),
    path('callback/', views.spotify_callback_view, name='spotify_callback'),
    path('player/current/', views.get_current_playback, name='player_current'),
    path('player/play-pause/', views.play_pause_playback, name='player_play_pause'),
    path('player/next/', views.next_track_playback, name='player_next'),
    path('player/previous/', views.previous_track_playback, name='player_previous'),
    path('player/start/', views.start_playback, name='player_start'),
]
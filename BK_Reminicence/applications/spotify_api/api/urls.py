from django.urls import path
from .views import (
    SpotifyAuthURLView,
    SpotifyCallbackView,
    SpotifyStatusView,
    CurrentPlaybackView,
    PlaySpotifyURIView,
    PausePlaybackView,
    NextTrackView,
    PreviousTrackView,
    SeekTrackView,
    ShufflePlaybackView,
    RepeatPlaybackView,
)

app_name = 'spotify_api'

urlpatterns = [
    # Autenticación
    path('auth/url/', SpotifyAuthURLView.as_view(), name='auth_url'),
    path('auth/callback/', SpotifyCallbackView.as_view(), name='callback'),
    path('status/', SpotifyStatusView.as_view(), name='status'),
    
    # Control del reproductor
    path('player/current/', CurrentPlaybackView.as_view(), name='current_playback'),
    path('player/play/', PlaySpotifyURIView.as_view(), name='play'),
    path('player/pause/', PausePlaybackView.as_view(), name='pause'),
    path('player/next/', NextTrackView.as_view(), name='next'),
    path('player/previous/', PreviousTrackView.as_view(), name='previous'),
    path('player/seek/', SeekTrackView.as_view(), name='seek'),
    path('player/shuffle/', ShufflePlaybackView.as_view(), name='shuffle'),
    path('player/repeat/', RepeatPlaybackView.as_view(), name='repeat'),
]

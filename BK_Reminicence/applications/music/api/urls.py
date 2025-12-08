from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ArtistViewSet,
    AlbumViewSet,
    SongViewSet,
    GenreViewSet,
    PlaylistViewSet,
    FavoriteSongsView,
    FavoriteArtistsView,
    SpotifySearchView,
    SyncSpotifyView,
    RecentlyPlayedView,
    RecommendationsView,
    MusicStatsView,
    TopItemsView,
    SongPlaylistsView
)

app_name = 'music'

router = DefaultRouter()
router.register('artists', ArtistViewSet, basename='artist')
router.register('albums', AlbumViewSet, basename='album')
router.register('songs', SongViewSet, basename='song')
router.register('genres', GenreViewSet, basename='genre')
router.register('playlists', PlaylistViewSet, basename='playlist')


urlpatterns = [
    path('', include(router.urls)),
    
    path('favorites/songs/', FavoriteSongsView.as_view(), name='favorite_songs'),
    path('favorites/artists/', FavoriteArtistsView.as_view(), name='favorite_artists'),
    
    path('search/', SpotifySearchView.as_view(), name='search'),
    path('sync/', SyncSpotifyView.as_view(), name='sync'),
    
    path('recent/', RecentlyPlayedView.as_view(), name='recent'),
    path('recommendations/', RecommendationsView.as_view(), name='recommendations'),
    path('stats/', MusicStatsView.as_view(), name='stats'),
    path('top/', TopItemsView.as_view(), name='top_items'),
    path('songs/<str:song_id>/playlists/', SongPlaylistsView.as_view(), name='song_playlists'),
]
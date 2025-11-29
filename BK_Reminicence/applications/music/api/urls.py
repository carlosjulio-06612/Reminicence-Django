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
)

app_name = 'music'

router = DefaultRouter()
router.register('artists', ArtistViewSet, basename='artist')
router.register('albums', AlbumViewSet, basename='album')
router.register('songs', SongViewSet, basename='song')
router.register('genres', GenreViewSet, basename='genre')
router.register('playlists', PlaylistViewSet, basename='playlist')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Favoritos
    path('favorites/songs/', FavoriteSongsView.as_view(), name='favorite_songs'),
    path('favorites/artists/', FavoriteArtistsView.as_view(), name='favorite_artists'),
    
    # Búsqueda
    path('search/', SpotifySearchView.as_view(), name='search'),
    
    # Sincronización
    path('sync/', SyncSpotifyView.as_view(), name='sync'),
]

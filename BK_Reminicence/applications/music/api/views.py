from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from ..models import (
    Artists,
    Albums,
    Songs,
    Genres,
    Playlist,
    PlaylistSong,
    UserFavoriteSong,
    UserFavoriteArtist
)
from applications.core import spotify_service as SpotifyService
from .serializers import (
    ArtistSerializer,
    AlbumSerializer,
    SongSerializer,
    SongMinimalSerializer,
    GenreSerializer,
    PlaylistSerializer,
    PlaylistDetailSerializer,
    PlaylistCreateSerializer,
    PlaylistUpdateSerializer,
    AddSongToPlaylistSerializer,
    FavoriteSongSerializer,
    FavoriteArtistSerializer,
    SpotifySearchResultSerializer,
    SyncStatusSerializer,
)


# ===================================================================
# ===== VIEWSETS PARA MODELOS BÁSICOS ===============================
# ===================================================================

class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para artistas
    
    list: Listar todos los artistas
    retrieve: Ver detalle de un artista
    """
    queryset = Artists.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'country']
    ordering_fields = ['name', 'popularity', 'followers']
    ordering = ['-popularity']
    
    @action(detail=True, methods=['get'])
    def albums(self, request, pk=None):
        """Obtener álbumes de un artista"""
        artist = self.get_object()
        albums = Albums.objects.filter(artist=artist)
        serializer = AlbumSerializer(albums, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def top_tracks(self, request, pk=None):
        """Obtener top tracks de un artista (desde Spotify)"""
        artist = self.get_object()
        
        if not artist.spotify_id:
            return Response(
                {'error': 'Este artista no tiene ID de Spotify'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spotify_service = SpotifyService(request.user)
            top_tracks = spotify_service.get_artist_top_tracks(artist.spotify_id)
            return Response(top_tracks)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AlbumViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para álbumes
    
    list: Listar todos los álbumes
    retrieve: Ver detalle de un álbum
    """
    queryset = Albums.objects.select_related('artist').all()
    serializer_class = AlbumSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'artist__name']
    ordering_fields = ['title', 'release_date', 'release_year']
    ordering = ['-release_date']
    
    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        """Obtener canciones de un álbum"""
        album = self.get_object()
        songs = Songs.objects.filter(album=album).order_by('track_number')
        serializer = SongSerializer(songs, many=True)
        return Response(serializer.data)


class SongViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para canciones
    
    list: Listar todas las canciones
    retrieve: Ver detalle de una canción
    """
    queryset = Songs.objects.select_related('album', 'album__artist').all()
    serializer_class = SongSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'album__artist__name', 'album__title']
    ordering_fields = ['title', 'popularity', 'duration']
    ordering = ['-popularity']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SongMinimalSerializer
        return SongSerializer


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para géneros
    
    list: Listar todos los géneros
    retrieve: Ver detalle de un género
    """
    queryset = Genres.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


# ===================================================================
# ===== VIEWSET DE PLAYLISTS ========================================
# ===================================================================

class PlaylistViewSet(viewsets.ModelViewSet):
    """
    ViewSet para playlists del usuario
    
    list: Listar mis playlists
    create: Crear nueva playlist
    retrieve: Ver detalle de una playlist
    update: Actualizar playlist
    destroy: Eliminar playlist
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Playlist.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PlaylistCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PlaylistUpdateSerializer
        elif self.action == 'retrieve':
            return PlaylistDetailSerializer
        return PlaylistSerializer
    
    def perform_create(self, serializer):
        """Asignar usuario al crear playlist"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_song(self, request, pk=None):
        """Agregar canción a la playlist"""
        playlist = self.get_object()
        serializer = AddSongToPlaylistSerializer(data=request.data)
        
        if serializer.is_valid():
            song_id = serializer.validated_data['song_id']
            song = get_object_or_404(Songs, id=song_id)
            
            # Verificar si la canción ya está en la playlist
            if PlaylistSong.objects.filter(playlist=playlist, song=song).exists():
                return Response(
                    {'error': 'La canción ya está en esta playlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Agregar canción
            PlaylistSong.objects.create(
                playlist=playlist,
                song=song,
                added_by=request.user
            )
            
            return Response({
                'message': f'Canción "{song.title}" agregada a "{playlist.name}"'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_song(self, request, pk=None):
        """Eliminar canción de la playlist"""
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response(
                {'error': 'Se requiere song_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            playlist_song = PlaylistSong.objects.get(
                playlist=playlist,
                song_id=song_id
            )
            song_title = playlist_song.song.title
            playlist_song.delete()
            
            return Response({
                'message': f'Canción "{song_title}" eliminada de "{playlist.name}"'
            })
        except PlaylistSong.DoesNotExist:
            return Response(
                {'error': 'La canción no está en esta playlist'},
                status=status.HTTP_404_NOT_FOUND
            )


# ===================================================================
# ===== VISTAS DE FAVORITOS =========================================
# ===================================================================

class FavoriteSongsView(APIView):
    """
    Vista para gestionar canciones favoritas
    
    GET: Listar canciones favoritas
    POST: Agregar canción a favoritos
    DELETE: Eliminar canción de favoritos
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Listar canciones favoritas del usuario"""
        favorites = UserFavoriteSong.objects.filter(
            user=request.user
        ).select_related('song__album__artist').order_by('-added_at')
        
        serializer = FavoriteSongSerializer(favorites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Agregar canción a favoritos"""
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response(
                {'error': 'Se requiere song_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        song = get_object_or_404(Songs, id=song_id)
        
        # Verificar si ya está en favoritos
        if UserFavoriteSong.objects.filter(user=request.user, song=song).exists():
            return Response(
                {'error': 'Esta canción ya está en tus favoritos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Agregar a favoritos
        favorite = UserFavoriteSong.objects.create(
            user=request.user,
            song=song
        )
        
        serializer = FavoriteSongSerializer(favorite)
        return Response({
            'message': f'Canción "{song.title}" agregada a favoritos',
            'favorite': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def delete(self, request):
        """Eliminar canción de favoritos"""
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response(
                {'error': 'Se requiere song_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            favorite = UserFavoriteSong.objects.get(
                user=request.user,
                song_id=song_id
            )
            song_title = favorite.song.title
            favorite.delete()
            
            return Response({
                'message': f'Canción "{song_title}" eliminada de favoritos'
            })
        except UserFavoriteSong.DoesNotExist:
            return Response(
                {'error': 'Esta canción no está en tus favoritos'},
                status=status.HTTP_404_NOT_FOUND
            )


class FavoriteArtistsView(APIView):
    """
    Vista para gestionar artistas favoritos
    
    GET: Listar artistas favoritos
    POST: Agregar artista a favoritos
    DELETE: Eliminar artista de favoritos
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Listar artistas favoritos del usuario"""
        favorites = UserFavoriteArtist.objects.filter(
            user=request.user
        ).select_related('artist').order_by('-added_at')
        
        serializer = FavoriteArtistSerializer(favorites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Agregar artista a favoritos"""
        artist_id = request.data.get('artist_id')
        
        if not artist_id:
            return Response(
                {'error': 'Se requiere artist_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        artist = get_object_or_404(Artists, id=artist_id)
        
        # Verificar si ya está en favoritos
        if UserFavoriteArtist.objects.filter(user=request.user, artist=artist).exists():
            return Response(
                {'error': 'Este artista ya está en tus favoritos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Agregar a favoritos
        favorite = UserFavoriteArtist.objects.create(
            user=request.user,
            artist=artist
        )
        
        serializer = FavoriteArtistSerializer(favorite)
        return Response({
            'message': f'Artista "{artist.name}" agregado a favoritos',
            'favorite': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def delete(self, request):
        """Eliminar artista de favoritos"""
        artist_id = request.data.get('artist_id')
        
        if not artist_id:
            return Response(
                {'error': 'Se requiere artist_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            favorite = UserFavoriteArtist.objects.get(
                user=request.user,
                artist_id=artist_id
            )
            artist_name = favorite.artist.name
            favorite.delete()
            
            return Response({
                'message': f'Artista "{artist_name}" eliminado de favoritos'
            })
        except UserFavoriteArtist.DoesNotExist:
            return Response(
                {'error': 'Este artista no está en tus favoritos'},
                status=status.HTTP_404_NOT_FOUND
            )


# ===================================================================
# ===== VISTAS DE BÚSQUEDA Y SINCRONIZACIÓN =========================
# ===================================================================

class SpotifySearchView(APIView):
    """
    Vista para buscar contenido en Spotify
    
    Query params:
    - q: Término de búsqueda
    - type: Tipo de contenido (track, artist, album) - default: track
    - limit: Cantidad de resultados (max: 50) - default: 20
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'track')
        limit = int(request.query_params.get('limit', 20))
        
        if not query:
            return Response(
                {'error': 'Se requiere el parámetro "q" para buscar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spotify_service = SpotifyService(request.user)
            results = spotify_service.search(query, search_type, limit)
            
            serializer = SpotifySearchResultSerializer(results)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncSpotifyView(APIView):
    """
    Vista para sincronizar datos de Spotify
    
    POST: Sincronizar playlists, artistas y canciones guardadas
    GET: Obtener estado de última sincronización
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener estado de última sincronización"""
        # Aquí podrías almacenar el estado de sync en un modelo
        # Por ahora retornamos info básica
        last_sync = {
            'user': request.user.username,
            'spotify_linked': hasattr(request.user, 'spotifyusertoken'),
            'last_sync_date': None,  # Implementar si tienes modelo de SyncHistory
        }
        
        serializer = SyncStatusSerializer(last_sync)
        return Response(serializer.data)
    
    def post(self, request):
        """Iniciar sincronización con Spotify"""
        sync_playlists = request.data.get('sync_playlists', True)
        sync_saved_tracks = request.data.get('sync_saved_tracks', True)
        sync_top_artists = request.data.get('sync_top_artists', True)
        
        try:
            spotify_service = SpotifyService(request.user)
            
            results = {
                'playlists_synced': 0,
                'tracks_synced': 0,
                'artists_synced': 0,
            }
            
            # Sincronizar según las opciones
            if sync_playlists:
                playlists = spotify_service.sync_user_playlists()
                results['playlists_synced'] = len(playlists)
            
            if sync_saved_tracks:
                tracks = spotify_service.sync_saved_tracks()
                results['tracks_synced'] = len(tracks)
            
            if sync_top_artists:
                artists = spotify_service.sync_top_artists()
                results['artists_synced'] = len(artists)
            
            return Response({
                'message': '¡Sincronización completada exitosamente!',
                'results': results
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al sincronizar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
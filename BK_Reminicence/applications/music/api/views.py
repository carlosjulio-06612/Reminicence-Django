from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum
from applications.music.sync_service import SpotifySyncService 
from applications.core.spotify_service import SpotifyService 
from ..models import PlaybackHistory, Devices 
from .serializers import PlaybackHistorySerializer
from django.db.models import Q, Count, Sum, Max
from django.utils import timezone
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
)


class ArtistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Artists.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'country']
    ordering_fields = ['name', 'popularity', 'followers']
    ordering = ['-popularity']
    
    def retrieve(self, request, pk=None):
        try:
            # Intento Local
            artist = Artists.objects.get(pk=pk)
            serializer = self.get_serializer(artist)
            return Response(serializer.data)
        except (Artists.DoesNotExist, ValueError):
            # Fallback Spotify
            try:
                spotify_service = SpotifyService(request.user)
                sp_artist = spotify_service.sp.artist(pk)
                
                return Response({
                    'id': sp_artist['id'],
                    'artist_id': sp_artist['id'],
                    'name': sp_artist['name'],
                    'image_url': sp_artist['images'][0]['url'] if sp_artist['images'] else '',
                    'spotify_id': sp_artist['id'],
                    'followers': sp_artist['followers']['total'],
                    'popularity': sp_artist['popularity'],
                    'genres': sp_artist['genres']
                })
            except Exception as e:
                return Response({'error': str(e)}, status=404)

    @action(detail=True, methods=['get'])
    def albums(self, request, pk=None):
        try:
            if str(pk).isdigit():
                artist = Artists.objects.get(pk=pk)
                albums = Albums.objects.filter(artist=artist)
                if albums.exists():
                    serializer = AlbumSerializer(albums, many=True)
                    return Response(serializer.data)
        except:
            pass 

        try:
            spotify_service = SpotifyService(request.user)
            results = spotify_service.sp.artist_albums(pk, album_type='album,single', limit=50)
            
            albums_data = []
            for item in results['items']:
                albums_data.append({
                    'id': item['id'],
                    'album_id': item['id'], 
                    'name': item['name'],
                    'title': item['name'],
                    'cover_image_url': item['images'][0]['url'] if item['images'] else '',
                    'image_url': item['images'][0]['url'] if item['images'] else '',
                    'release_year': item['release_date'][:4] if item['release_date'] else '',
                    'spotify_id': item['id'],
                    'total_tracks': item['total_tracks']
                })
            return Response(albums_data)
        except Exception as e:
            return Response({'error': str(e)}, status=404)
    
    @action(detail=True, methods=['get'])
    def top_tracks(self, request, pk=None):
        try:
            spotify_service = SpotifyService(request.user)
            spotify_id = pk
            
            if str(pk).isdigit():
                artist = get_object_or_404(Artists, pk=pk)
                spotify_id = artist.spotify_id

            top_tracks = spotify_service.get_artist_top_tracks(spotify_id)
            
            mapped_tracks = []
            for t in top_tracks:
                mapped_tracks.append({
                    'song_id': t['id'],
                    'id': t['id'],
                    'title': t.get('name', ''),
                    'artist_name': t.get('artist_name', 'Artista'),
                    'album_cover': t.get('image', ''),
                    'duration': t.get('duration_ms', 0),
                    'duration_ms': t.get('duration_ms', 0),
                    'popularity': t.get('popularity', 0),
                    'spotify_uri': t.get('uri', '')
                })
            return Response(mapped_tracks)
        except Exception as e:
            return Response({'error': str(e)}, status=404)


class AlbumViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Albums.objects.select_related('artist').all()
    serializer_class = AlbumSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'artist__name']
    ordering_fields = ['title', 'release_date', 'release_year']
    ordering = ['-release_date']
    
    def retrieve(self, request, pk=None):
        # 1. INTENTO DE BASE DE DATOS LOCAL
        try:
            album = Albums.objects.get(pk=pk)
            serializer = self.get_serializer(album)
            data = serializer.data
            
            # --- NORMALIZACIÓN DE DATOS (FIX PARA FRONTEND) ---
            # El frontend espera 'artists' (array) e 'images' (array) como Spotify.
            # El serializer devuelve 'artist' (objeto) y 'cover_image_url' (string).
            
            # Crear estructura de artistas compatible
            if 'artist' in data and data['artist']:
                data['artists'] = [data['artist']]
            else:
                data['artists'] = [{'name': 'Desconocido'}]
                
            # Crear estructura de imágenes compatible
            if 'cover_image_url' in data:
                data['images'] = [{'url': data['cover_image_url']}]
                data['image_url'] = data['cover_image_url'] # Fallback adicional
            
            # Asegurar nombre
            if 'title' in data:
                data['name'] = data['title']

            return Response(data)
            
        except (Albums.DoesNotExist, ValueError):
            # 2. FALLBACK A SPOTIFY
            try:
                spotify_service = SpotifyService(request.user)
                sp_album = spotify_service.sp.album(pk)
                
                return Response({
                    'id': sp_album['id'],
                    'album_id': sp_album['id'],
                    'name': sp_album['name'],
                    'title': sp_album['name'],
                    'image_url': sp_album['images'][0]['url'] if sp_album['images'] else '',
                    'images': sp_album['images'], # Importante para el frontend
                    'artists': [{'id': a['id'], 'name': a['name']} for a in sp_album['artists']],
                    'artist_name': sp_album['artists'][0]['name'] if sp_album['artists'] else 'Varios Artistas',
                    'release_date': sp_album['release_date'],
                    'release_year': sp_album['release_date'][:4] if sp_album['release_date'] else '',
                    'total_tracks': sp_album['total_tracks'],
                    'label': sp_album['label'],
                    'genres': sp_album.get('genres', []),
                    'popularity': sp_album['popularity'],
                    'uri': sp_album['uri'],
                    'album_type': sp_album['album_type']
                })
            except Exception as e:
                return Response({'error': str(e)}, status=404)

    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        # 1. INTENTO LOCAL
        try:
            if str(pk).isdigit():
                album = Albums.objects.get(pk=pk)
                songs = Songs.objects.filter(album=album).order_by('track_number')
                
                if songs.exists():
                    serializer = SongSerializer(songs, many=True)
                    data = serializer.data
                    
                    # --- NORMALIZACIÓN DE TRACKS ---
                    # El frontend espera 'artists' array en cada track
                    for track in data:
                        # Convertir artist_name en estructura de array
                        track['artists'] = [{'name': track.get('artist_name', 'Desconocido')}]
                        # Asegurar duration_ms
                        if 'duration' in track:
                            track['duration_ms'] = track['duration']
                            
                    return Response(data)
        except:
            pass
            
        # 2. FALLBACK SPOTIFY
        try:
            spotify_service = SpotifyService(request.user)
            results = spotify_service.sp.album_tracks(pk)
            
            tracks_data = []
            for t in results['items']:
                tracks_data.append({
                    'song_id': t['id'],
                    'id': t['id'],
                    'title': t['name'],
                    'name': t['name'], # Frontend usa title o name
                    'duration': t['duration_ms'],
                    'duration_ms': t['duration_ms'],
                    'track_number': t['track_number'],
                    'spotify_uri': t['uri'],
                    'artists': [{'name': a['name']} for a in t['artists']]
                })
            return Response(tracks_data)
        except Exception as e:
            return Response({'error': str(e)}, status=404)


class SongViewSet(viewsets.ReadOnlyModelViewSet):
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
    
    @action(detail=True, methods=['get'])
    def audio_features(self, request, pk=None):
        song = self.get_object()
        
        if not song.spotify_id:
            return Response({'error': 'Canción sin ID de Spotify'}, status=400)
            
        try:
            spotify_service = SpotifyService(request.user)
            features = spotify_service.sp.audio_features([song.spotify_id])
            if features and features[0]:
                return Response(features[0])
            return Response({'error': 'No se encontraron características'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Genres.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    @action(detail=True, methods=['get'])
    def songs(self, request, pk=None):
        genre = self.get_object()
        songs = genre.songs.select_related('album', 'album__artist').all().order_by('-popularity')[:50]
        serializer = SongMinimalSerializer(songs, many=True)
        return Response(serializer.data)


class PlaylistViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, pk=None):
            try:
                playlist = Playlist.objects.get(pk=pk)
                if playlist.user != request.user and playlist.status == 'private':
                    return Response({'error': 'No tienes permiso'}, status=403)
                serializer = PlaylistDetailSerializer(playlist)
                data = serializer.data
                
                # Normalización para playlist local
                if 'cover_image_url' in data:
                    data['images'] = [{'url': data['cover_image_url']}]
                
                return Response(data)
                
            except (Playlist.DoesNotExist, ValueError):
                try:
                    spotify_service = SpotifyService(request.user)
                    sp_playlist = spotify_service.sp.playlist(pk)
                    
                    songs_data = []
                    for item in sp_playlist['tracks']['items']:
                        if not item['track']: 
                            continue
                        track = item['track']
                        
                        artists_with_ids = [
                            {
                                'id': a['id'],
                                'artist_id': a['id'],  # Alias adicional
                                'spotify_id': a['id'],  # Alias adicional
                                'name': a['name'],
                                'uri': a.get('uri', '')
                            } for a in track['artists']
                        ]
                        
                        album_data = {
                            'id': track['album']['id'],
                            'album_id': track['album']['id'],  # Alias adicional
                            'spotify_id': track['album']['id'],  # Alias adicional
                            'name': track['album']['name'],
                            'images': track['album']['images']
                        }
                        
                        songs_data.append({
                            'song': {
                                'song_id': track['id'],
                                'id': track['id'],
                                'spotify_id': track['id'],
                                'title': track['name'],
                                'name': track['name'],  # Alias
                                'duration': track['duration_ms'],
                                'duration_ms': track['duration_ms'],
                                'uri': track['uri'],
                                'preview_url': track.get('preview_url'),
                                'explicit_content': track.get('explicit', False),
                                
                                'artist_id': artists_with_ids[0]['id'] if artists_with_ids else None,
                                'artist_name': artists_with_ids[0]['name'] if artists_with_ids else 'Desconocido',
                                'artists': artists_with_ids,
                                
                                'album_id': album_data['id'],
                                'album': album_data,
                                'album_title': album_data['name'],
                                'album_name': album_data['name'],
                                'album_cover': track['album']['images'][0]['url'] if track['album']['images'] else '',
                            },
                            'date_added': item['added_at'],
                            'added_at': item['added_at']
                        })

                    return Response({
                        'id': sp_playlist['id'],
                        'playlist_id': sp_playlist['id'],
                        'name': sp_playlist['name'],
                        'description': sp_playlist['description'],
                        'cover_image_url': sp_playlist['images'][0]['url'] if sp_playlist['images'] else '',
                        'images': sp_playlist['images'],
                        'owner': sp_playlist['owner']['display_name'],
                        'user': sp_playlist['owner']['display_name'],
                        'songs': songs_data
                    })
                    
                except Exception as e:
                    return Response({'error': f'Playlist no encontrada: {str(e)}'}, status=404)
    
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
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='add_song')
    def add_song(self, request, pk=None):
        """
        Agregar canción a playlist (soporta Spotify IDs y PKs locales)
        """
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response({'error': 'Se requiere song_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if str(song_id).isdigit():
                song = Songs.objects.get(pk=song_id)
            else:
                song = Songs.objects.filter(spotify_id=song_id).first()
                
                if not song:
                    spotify_service = SpotifyService(request.user)
                    track_data = spotify_service.sp.track(song_id)
                    
                    artist_spotify_id = track_data['artists'][0]['id']
                    artist, _ = Artists.objects.get_or_create(
                        spotify_id=artist_spotify_id,
                        defaults={
                            'name': track_data['artists'][0]['name'], 
                            'image_url': '',
                            'data_source': 'spotify'
                        }
                    )
                    
                    album_spotify_id = track_data['album']['id']
                    album, _ = Albums.objects.get_or_create(
                        spotify_id=album_spotify_id,
                        defaults={
                            'title': track_data['album']['name'],
                            'artist': artist,
                            'cover_image_url': track_data['album']['images'][0]['url'] if track_data['album']['images'] else '',
                            'release_date': track_data['album']['release_date'],
                            'data_source': 'spotify'
                        }
                    )
                    
                    song = Songs.objects.create(
                        spotify_id=song_id,
                        title=track_data['name'],
                        album=album,
                        duration=track_data['duration_ms'],
                        spotify_uri=track_data['uri'],
                        preview_url=track_data.get('preview_url'),
                        explicit_content=track_data.get('explicit', False),
                        data_source='spotify'
                    )
            if PlaylistSong.objects.filter(playlist=playlist, song=song).exists():
                return Response({'error': 'La canción ya está en esta playlist'}, status=status.HTTP_400_BAD_REQUEST)
            
            max_pos = PlaylistSong.objects.filter(playlist=playlist).aggregate(Max('position'))['position__max']
            new_position = (max_pos or 0) + 1

            PlaylistSong.objects.create(
                playlist=playlist,
                song=song,
                added_by_user=request.user,  
                position=new_position,     
                date_added=timezone.now()   
            )
            
            return Response({'message': f'Canción "{song.title}" agregada a "{playlist.name}"'}, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Imprimir error en consola del servidor para debug
            print(f"Error adding song: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'], url_path='remove_song')
    def remove_song(self, request, pk=None):
        """
        Eliminar canción de playlist (soporta Spotify IDs y PKs locales)
        """
        playlist = self.get_object()
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response(
                {'error': 'Se requiere song_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Buscar la relación específica
            if str(song_id).isdigit():
                playlist_song = PlaylistSong.objects.filter(
                    playlist=playlist,
                    song__pk=song_id
                ).first()
            else:
                playlist_song = PlaylistSong.objects.filter(
                    playlist=playlist,
                    song__spotify_id=song_id
                ).first()
            
            if not playlist_song:
                return Response(
                    {'error': 'La canción no está en esta playlist'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            song_title = playlist_song.song.title
            playlist_song.delete()
            
            return Response({
                'message': f'Canción "{song_title}" eliminada de "{playlist.name}"'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FavoriteSongsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        favorites = UserFavoriteSong.objects.filter(
            user=request.user
        ).select_related('song__album__artist').order_by('-added_at')
        
        serializer = FavoriteSongSerializer(favorites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        song_id = request.data.get('song_id')
        
        if not song_id:
            return Response(
                {'error': 'Se requiere song_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        song = get_object_or_404(Songs, id=song_id)
        
        if UserFavoriteSong.objects.filter(user=request.user, song=song).exists():
            return Response(
                {'error': 'Esta canción ya está en tus favoritos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        favorites = UserFavoriteArtist.objects.filter(
            user=request.user
        ).select_related('artist').order_by('-favorited_at')
        
        serializer = FavoriteArtistSerializer(favorites, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        artist_id = request.data.get('artist_id')
        
        if not artist_id:
            return Response(
                {'error': 'Se requiere artist_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        artist = get_object_or_404(Artists, id=artist_id)
        
        if UserFavoriteArtist.objects.filter(user=request.user, artist=artist).exists():
            return Response(
                {'error': 'Este artista ya está en tus favoritos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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


class SpotifySearchView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '')
        limit = int(request.query_params.get('limit', 10))
        
        if not query:
            return Response(
                {'error': 'Se requiere el parámetro "q" para buscar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            spotify_service = SpotifyService(request.user)
            spotify_results = spotify_service.search_spotify(query, limit=limit)
            
            response_data = {
                'tracks': {
                    'results': [
                        {
                            'song_id': t['id'],
                            'id': t['id'],
                            'title': t['name'],
                            'artist_name': t.get('artist', ''),
                            'album_name': (
                                t.get('album', {}).get('name', 'Álbum desconocido')
                                if isinstance(t.get('album'), dict)
                                else t.get('album', 'Álbum desconocido')
                            ),
                            'album_cover': (
                                t.get('album', {}).get('image', '')
                                or t.get('image', '')
                            ),
                            'spotify_uri': t['uri'],
                            'duration': t.get('duration_formatted', '0:00'),
                            'duration_ms': t.get('duration_ms', 0)
                        } for t in spotify_results.get('tracks', [])
                    ]
                },
                'artists': {
                    'results': [
                        {
                            'artist_id': a['id'],
                            'id': a['id'],
                            'name': a['name'],
                            'image_url': a.get('image', ''),
                            'spotify_uri': a['uri']
                        } for a in spotify_results.get('artists', [])
                    ]
                },
                'albums': {
                    'results': [
                        {
                            'id': a['id'],
                            'album_id': a['id'],
                            'name': a['name'],
                            'artist_name': (
                                ', '.join(artist['name'] for artist in a.get('artists', []) if 'name' in artist)
                                if a.get('artists')
                                else a.get('artist', {}).get('name', 'Artista desconocido')
                            ),
                            'image': (
                                a.get('image')
                                or (a['images'][0]['url'] if a.get('images') else '')
                            ),
                            'cover_image_url': (
                                a.get('image')
                                or (a['images'][0]['url'] if a.get('images') else '')
                            ),
                            'release_year': a.get('release_year', '')
                        } for a in spotify_results.get('albums', [])
                    ]
                },
                'playlists': {
                    'results': [
                        {
                            'playlist_id': p['id'],
                            'id': p['id'],
                            'name': p['name'],
                            'image_url': p.get('image', ''),
                            'owner': p.get('owner', ''),
                            'total_tracks': p.get('tracks', 0)
                        } for p in spotify_results.get('playlists', [])
                    ]
                }
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncSpotifyView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        last_sync = {
            'user': request.user.username,
            'spotify_linked': True,
            'last_sync_date': timezone.now(),
            'is_syncing': False,
            'playlists_synced': 0,
            'message': "Listo para sincronizar"
        }
        return Response(last_sync)
    
    def post(self, request):
        sync_playlists_opt = request.data.get('sync_playlists', True)
        sync_saved_tracks_opt = request.data.get('sync_saved_tracks', True)
        sync_top_artists_opt = request.data.get('sync_top_artists', True)
        
        try:
            sync_service = SpotifySyncService(request.user)
            
            results = {
                'playlists_synced': 0,
                'tracks_synced': 0,
                'artists_synced': 0,
            }
            
            if sync_playlists_opt:
                count = sync_service.sync_playlists()
                results['playlists_synced'] = count
            
            if sync_saved_tracks_opt:
                count = sync_service.sync_saved_tracks()
                results['tracks_synced'] = count
            
            if sync_top_artists_opt:
                count = sync_service.sync_top_artists()
                results['artists_synced'] = count
            
            return Response({
                'message': '¡Sincronización completada exitosamente!',
                'results': results
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al sincronizar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecentlyPlayedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get('limit', 20))
        
        try:
            spotify_service = SpotifyService(request.user)
            recent_tracks = spotify_service.sp.current_user_recently_played(limit=limit)
            
            return Response(recent_tracks)
            
        except Exception as e:
            print(f"Error fetching Spotify recent: {e}")
            
            history = PlaybackHistory.objects.filter(user=request.user)\
                .select_related('song', 'song__album', 'song__album__artist')\
                .order_by('-playback_date')[:limit]
            
            if not history.exists():
                return Response({'items': []})

            serializer = PlaybackHistorySerializer(history, many=True)
            return Response({'items': serializer.data})

    def post(self, request):
        song_id = request.data.get('song_id')
        if not song_id:
            return Response({'error': 'song_id requerido'}, status=400)
        song = get_object_or_404(Songs, song_id=song_id)
        
        device, _ = Devices.objects.get_or_create(
            device_name="Web Player", 
            defaults={'device_type': 'Computer', 'operating_system': 'Web'}
        )

        PlaybackHistory.objects.create(
            user=request.user,
            song=song,
            device=device,
            playback_date=timezone.now(),
            completed=False,
            playback_duration=0
        )
        return Response({'status': 'added_to_history'}, status=201)

class RecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            limit = int(request.query_params.get('limit', 10))
            seed_tracks = request.query_params.get('seed_tracks', None)
            seed_artists = request.query_params.get('seed_artists', None)
            seed_genres = request.query_params.get('seed_genres', None)

            if not (seed_tracks or seed_artists or seed_genres):
                top_tracks = spotify_service.sp.current_user_top_tracks(limit=2)
                if top_tracks['items']:
                    seed_tracks = ",".join([t['id'] for t in top_tracks['items']])
            
            kwrgs = {'limit': limit}
            if seed_tracks: kwrgs['seed_tracks'] = seed_tracks.split(',')[:5]
            if seed_artists: kwrgs['seed_artists'] = seed_artists.split(',')[:5]
            if seed_genres: kwrgs['seed_genres'] = seed_genres.split(',')[:5]

            if not kwrgs.get('seed_tracks') and not kwrgs.get('seed_artists') and not kwrgs.get('seed_genres'):
                 return Response({'results': []})

            recs = spotify_service.sp.recommendations(**kwrgs)
            
            tracks_formatted = []
            for t in recs['tracks']:
                tracks_formatted.append({
                    'song_id': t['id'],
                    'id': t['id'],
                    'title': t['name'],
                    'artist_name': t['artists'][0]['name'],
                    'album_cover': t['album']['images'][0]['url'] if t['album']['images'] else '',
                    'spotify_uri': t['uri'],
                    'duration_ms': t['duration_ms']
                })

            return Response({'tracks': tracks_formatted})
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class MusicStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        total_plays = PlaybackHistory.objects.filter(user=user).count()
        
        total_duration = PlaybackHistory.objects.filter(user=user).aggregate(
            total=Sum('song__duration')
        )['total'] or 0
        total_minutes = int(total_duration / 60000)

        total_favs = UserFavoriteSong.objects.filter(user=user).count()

        fav_genre = "Pop"
        top_genre_qs = Genres.objects.filter(
            songs__userfavoritesong__user=user
        ).annotate(count=Count('id')).order_by('-count')
        
        if top_genre_qs.exists():
            fav_genre = top_genre_qs.first().name

        data = {
            'total_songs_played': total_plays,
            'total_minutes_listened': total_minutes,
            'favorite_genre': fav_genre,
            'total_favorites': total_favs
        }
        return Response(data)


class TopItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        type_ = request.query_params.get('type', 'tracks')
        time_range = request.query_params.get('time_range', 'short_term')
        limit = int(request.query_params.get('limit', 10))

        try:
            spotify_service = SpotifyService(request.user)
            
            if type_ == 'artists':
                results = spotify_service.sp.current_user_top_artists(
                    limit=limit, time_range=time_range
                )
                items = [{
                    'id': i['id'], 
                    'name': i['name'], 
                    'image': i['images'][0]['url'] if i['images'] else '',
                    'image_url': i['images'][0]['url'] if i['images'] else ''
                } for i in results['items']]
            else:
                results = spotify_service.sp.current_user_top_tracks(
                    limit=limit, time_range=time_range
                )
                items = [{
                    'id': i['id'], 
                    'song_id': i['id'],
                    'title': i['name'], 
                    'artist': i['artists'][0]['name'],
                    'artist_name': i['artists'][0]['name'],
                    'image': i['album']['images'][0]['url'] if i['album']['images'] else '',
                    'album_cover': i['album']['images'][0]['url'] if i['album']['images'] else ''
                } for i in results['items']]

            return Response({'items': items})
            
        except Exception as e:
            return Response({'items': []})


class AlbumPageView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        try:
            spotify_service = SpotifyService(request.user)
            
            album_data = spotify_service.sp.album(id)
            tracks_data = spotify_service.sp.album_tracks(id)
            
            album_response = {
                'id': album_data['id'],
                'album_id': album_data['id'],
                'name': album_data['name'],
                'album_type': album_data['album_type'],
                'images': album_data['images'],
                'image_url': album_data['images'][0]['url'] if album_data['images'] else '',
                'artists': [
                    {
                        'id': a['id'],
                        'name': a['name'],
                        'images': a.get('images', [])
                    } for a in album_data['artists']
                ],
                'release_date': album_data['release_date'],
                'release_year': album_data['release_date'][:4] if album_data['release_date'] else '',
                'total_tracks': album_data['total_tracks'],
                'label': album_data.get('label', ''),
                'genres': album_data.get('genres', []),
                'popularity': album_data.get('popularity', 0),
                'uri': album_data['uri'],
                'copyrights': album_data.get('copyrights', []),
                'available_markets': album_data.get('available_markets', [])
            }
            
            tracks_response = []
            for track in tracks_data['items']:
                track_info = {
                    'id': track['id'],
                    'song_id': track['id'],
                    'title': track['name'],
                    'name': track['name'],
                    'duration': track['duration_ms'],
                    'duration_ms': track['duration_ms'],
                    'track_number': track['track_number'],
                    'uri': track['uri'],
                    'artists': [
                        {
                            'id': a['id'],
                            'name': a['name']
                        } for a in track['artists']
                    ],
                    'album': {
                        'id': album_data['id'],
                        'name': album_data['name'],
                        'images': album_data['images']
                    }
                }
                
                if len(tracks_response) < 5:
                    try:
                        track_features = spotify_service.sp.audio_features([track['id']])
                        if track_features and track_features[0]:
                            track_info['popularity'] = track_features[0].get('popularity', 0)
                            track_info['audio_features'] = track_features[0]
                    except:
                        pass
                
                tracks_response.append(track_info)
            
            
            
            return Response({
                'album': album_response,
                'tracks': tracks_response
            })
        
            
        except Exception as e:
            return Response({'error': str(e)}, status=404)


class SongPlaylistsView(APIView):
    """
    Endpoint para obtener las playlists que contienen una canción específica
    Soporta tanto PKs locales como Spotify IDs
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, song_id):
        """
        GET /api/music/songs/{song_id}/playlists/
        Retorna lista de IDs de playlists que contienen esta canción
        """
        try:
            # 🎯 Buscar por PK o Spotify ID
            if str(song_id).isdigit():
                playlist_ids = PlaylistSong.objects.filter(
                    playlist__user=request.user,
                    song__pk=song_id
                ).values_list('playlist_id', flat=True)
            else:
                playlist_ids = PlaylistSong.objects.filter(
                    playlist__user=request.user,
                    song__spotify_id=song_id
                ).values_list('playlist_id', flat=True)
            
            return Response({
                'song_id': song_id,
                'playlist_ids': list(playlist_ids)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
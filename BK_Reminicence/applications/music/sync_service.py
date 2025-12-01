import logging
from django.utils import timezone
from datetime import datetime
from applications.core.spotify_service import SpotifyService
from .models import (
    Artists, Albums, Songs, Playlist, PlaylistSong, 
    UserFavoriteSong, UserFavoriteArtist
)

logger = logging.getLogger(__name__)

class SpotifySyncService:
    """Servicio para sincronizar datos de Spotify con la base de datos local"""
    
    def __init__(self, user):
        self.user = user
        self.spotify_service = SpotifyService(user)

    # ==========================================
    # HELPER METHODS (Guardado de Entidades Base)
    # ==========================================

    def _sync_artist(self, artist_data):
        """Sincroniza un artista."""
        if not artist_data or not artist_data.get('id'):
            return None
            
        image_url = None
        if artist_data.get('images'):
            image_url = artist_data['images'][0]['url']
            
        artist, created = Artists.objects.update_or_create(
            spotify_id=artist_data['id'],
            defaults={
                'name': artist_data.get('name', 'Nombre no disponible'),
                'spotify_url': artist_data.get('external_urls', {}).get('spotify'),
                'image_url': image_url,
                'popularity': artist_data.get('popularity'),
                'data_source': 'spotify',
            }
        )
        return artist

    def _sync_album(self, album_data, artist_obj):
        """Sincroniza un álbum."""
        if not album_data or not album_data.get('id'):
            return None

        release_date_str = album_data.get('release_date')
        release_date_obj = None
        year = None
        
        if release_date_str:
            try:
                if len(release_date_str) > 4:
                    release_date_obj = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                    year = release_date_obj.year
                else:
                    year = int(release_date_str[:4])
                    release_date_obj = datetime(year, 1, 1).date()
            except (ValueError, TypeError):
                pass

        image_url = None
        if album_data.get('images'):
            image_url = album_data['images'][0]['url']

        album, created = Albums.objects.update_or_create(
            spotify_id=album_data['id'],
            defaults={
                'artist': artist_obj,
                'title': album_data.get('name', 'Título no disponible'),
                'release_date': release_date_obj,
                'release_year': year,
                'album_type': album_data.get('album_type'),
                'cover_image_url': image_url,
                'total_tracks': album_data.get('total_tracks'),
                'spotify_url': album_data.get('external_urls', {}).get('spotify'),
                'data_source': 'spotify',
            }
        )
        return album

    def sync_song(self, track_data):
        """Sincroniza una canción individual."""
        spotify_id = track_data.get('id')
        if not spotify_id:
            return None

        # Sincronizar Artista
        artist_data = track_data['artists'][0] if track_data.get('artists') else None
        if not artist_data:
            return None
        artist_obj = self._sync_artist(artist_data)
        
        # Sincronizar Álbum
        album_data = track_data.get('album', {})
        album_obj = self._sync_album(album_data, artist_obj)

        # Sincronizar Canción
        song, created = Songs.objects.update_or_create(
            spotify_id=spotify_id,
            defaults={
                'album': album_obj,
                'title': track_data.get('name', ''),
                'duration': track_data.get('duration_ms', 0),
                'track_number': track_data.get('track_number'),
                'disc_number': track_data.get('disc_number'),
                'explicit_content': track_data.get('explicit', False),
                'preview_url': track_data.get('preview_url'),
                'spotify_url': track_data.get('external_urls', {}).get('spotify'),
                'popularity': track_data.get('popularity', 0),
                'data_source': 'spotify',
            }
        )
        return song
    
    # ==========================================
    # PLAYLISTS
    # ==========================================

    def sync_playlists(self):
        """Sincroniza playlists del usuario."""
        logger.info(f"Sync playlists para {self.user.username}")
        
        # Usamos el servicio core para obtener datos crudos
        spotify_playlists_raw = self.spotify_service.sp.current_user_playlists(limit=20)
        if not spotify_playlists_raw:
            return 0
        
        synced_count = 0
        for pl_data in spotify_playlists_raw['items']:
            try:
                image_url = pl_data['images'][0]['url'] if pl_data.get('images') else None
                
                playlist, created = Playlist.objects.update_or_create(
                    spotify_id=pl_data['id'],
                    defaults={
                        'user': self.user, # Importante: asignar al usuario
                        'name': pl_data['name'],
                        'description': pl_data.get('description', ''),
                        'cover_image_url': image_url,
                        'spotify_snapshot_id': pl_data.get('snapshot_id'),
                        'is_synced_with_spotify': True,
                        'last_sync_date': timezone.now(),
                        'status': 'public' if pl_data.get('public') else 'private'
                    }
                )

                self._sync_playlist_tracks(playlist, pl_data['id'])
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error playlist {pl_data.get('name')}: {e}")
                continue
        
        return synced_count
    
    def _sync_playlist_tracks(self, playlist, spotify_playlist_id):
        """Sincroniza canciones de una playlist."""
        try:
            sp = self.spotify_service.sp
            if not sp: return
            
            # Obtener tracks (paginación simple para ejemplo)
            results = sp.playlist_items(spotify_playlist_id, limit=100)
            tracks = results['items']
            
            # Limpiar anteriores para evitar duplicados de posición
            PlaylistSong.objects.filter(playlist=playlist).delete()
            
            playlist_songs_batch = []
            
            for idx, item in enumerate(tracks):
                track = item.get('track')
                if not track or track.get('is_local'): 
                    continue
                
                song_obj = self.sync_song(track)
                
                if song_obj:
                    date_added = item.get('added_at') or timezone.now()
                    
                    playlist_songs_batch.append(PlaylistSong(
                        playlist=playlist,
                        song=song_obj,
                        position=idx,
                        date_added=date_added,
                        added_by_user=self.user
                    ))
            
            PlaylistSong.objects.bulk_create(playlist_songs_batch)
                    
        except Exception as e:
            logger.error(f"Error tracks playlist '{playlist.name}': {e}")

    # ==========================================
    # FAVORITOS (Tracks & Artists)
    # ==========================================

    def sync_saved_tracks(self):
        """Sincroniza canciones 'Me gusta'."""
        sp = self.spotify_service.sp
        if not sp: return 0

        try:
            results = sp.current_user_saved_tracks(limit=50)
            count = 0
            for item in results['items']:
                track = item['track']
                song_obj = self.sync_song(track)
                
                if song_obj:
                    UserFavoriteSong.objects.get_or_create(
                        user=self.user,
                        song=song_obj,
                        defaults={'favorited_at': item.get('added_at') or timezone.now()}
                    )
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Error sync saved tracks: {e}")
            return 0

    def sync_top_artists(self):
        """Sincroniza artistas más escuchados."""
        sp = self.spotify_service.sp
        if not sp: return 0

        try:
            results = sp.current_user_top_artists(limit=20, time_range='medium_term')
            count = 0
            for artist_data in results['items']:
                artist_obj = self._sync_artist(artist_data)
                
                if artist_obj:
                    UserFavoriteArtist.objects.get_or_create(
                        user=self.user,
                        artist=artist_obj,
                        defaults={'favorited_at': timezone.now()}
                    )
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Error sync top artists: {e}")
            return 0
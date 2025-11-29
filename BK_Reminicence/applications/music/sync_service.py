from django.utils import timezone
from .models import Artists, Albums, Songs, Playlist, PlaylistSong
from applications.core.spotify_service import SpotifyService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SpotifySyncService:
    """Servicio para sincronizar datos de Spotify con la base de datos"""
    
    def __init__(self, user):
        self.user = user
        self.spotify_service = SpotifyService(user)

    def _sync_artist(self, artist_data):
        """Sincroniza un artista usando la información del track."""
        artist, created = Artists.objects.update_or_create(
            spotify_id=artist_data['id'],
            defaults={
                'name': artist_data.get('name', 'Nombre no disponible'),
                'spotify_url': artist_data.get('external_urls', {}).get('spotify'),
                'data_source': 'spotify',
            }
        )
        return artist

    def _sync_album(self, album_data, artist_obj):
        """Sincroniza un álbum."""
        release_date_str = album_data.get('release_date')
        release_date_obj = None
        year = None
        
        if release_date_str:
            try:
                if len(release_date_str) > 4:
                    release_date_obj = datetime.strptime(release_date_str, '%Y-%m-%d').date()
                    year = release_date_obj.year
                else:
                    year = int(release_date_str)
                    release_date_obj = datetime(year, 1, 1).date()
            except (ValueError, TypeError):
                release_date_obj = None
                year = None

        album, created = Albums.objects.update_or_create(
            spotify_id=album_data['id'],
            defaults={
                'artist': artist_obj,
                'title': album_data.get('name', 'Título no disponible'),
                'release_date': release_date_obj,
                'release_year': year,
                'album_type': album_data.get('album_type'),
                'cover_image_url': album_data['images'][0]['url'] if album_data.get('images') else None,
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

        artist_data = track_data['artists'][0] if track_data.get('artists') else None
        if not artist_data:
            return None
            
        artist_obj = self._sync_artist(artist_data)
        album_data = track_data.get('album', {})
        album_obj = self._sync_album(album_data, artist_obj)

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
                'isrc': track_data.get('external_ids', {}).get('isrc'),
                'data_source': 'spotify',
            }
        )
        return song
    
    def sync_playlists(self):
        """Sincroniza la metadata de todas las playlists del usuario."""
        logger.info(f"Iniciando sincronización de playlists para {self.user.username}")
        
        spotify_playlists = self.spotify_service.get_user_playlists()
        if not spotify_playlists:
            logger.warning(f"No se encontraron playlists para {self.user.username}")
            return 0
        
        synced_count = 0
        for pl_data in spotify_playlists:
            try:
                playlist, created = Playlist.objects.update_or_create(
                    user=self.user,
                    name=pl_data['name'],
                    defaults={
                        'spotify_id': pl_data['id'], 
                        'description': pl_data.get('description', ''),
                        'cover_image_url': pl_data.get('image'),
                        'spotify_snapshot_id': pl_data.get('snapshot_id'),
                        'is_synced_with_spotify': True,
                        'last_sync_date': timezone.now(),
                    }
                )

                self._sync_playlist_tracks(playlist, pl_data['id'])
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error al procesar playlist {pl_data.get('name')}: {e}")
                continue
        
        logger.info(f"Sincronización completada: {synced_count} playlists para {self.user.username}")
        return synced_count
    
    def _sync_playlist_tracks(self, playlist, spotify_playlist_id):
        """Sincroniza todas las canciones de una playlist específica."""
        try:
            sp = self.spotify_service.sp
            if not sp: 
                return
            
            results = sp.playlist_tracks(spotify_playlist_id)
            tracks = results['items']
            
            PlaylistSong.objects.filter(playlist=playlist).delete()
            
            songs_added_count = 0
            for idx, item in enumerate(tracks):
                track = item.get('track')
                if not track: 
                    continue
                
                song_obj = self.sync_song(track)
                
                if song_obj:
                    date_added_str = item.get('added_at')
                    date_added = timezone.now()
                    
                    if date_added_str:
                        try:
                            date_added = timezone.datetime.fromisoformat(
                                date_added_str.replace('Z', '+00:00')
                            )
                        except (ValueError, AttributeError):
                            pass
                    
                    PlaylistSong.objects.get_or_create(
                        playlist=playlist,
                        song=song_obj,
                        defaults={
                            'position': idx + 1,
                            'date_added': date_added,
                        }
                    )
                    songs_added_count += 1
                    
        except Exception as e:
            logger.error(f"Error sincronizando tracks de '{playlist.name}': {e}")
    
    def full_sync(self):
        """Realiza la sincronización completa."""
        logger.info(f"Sincronización completa iniciada para {self.user.username}")
        results = {'playlists': self.sync_playlists()}
        logger.info(f"Sincronización completada para {self.user.username}: {results['playlists']} playlists")
        return results
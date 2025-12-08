import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import time
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class SpotifyService:
    """
    Servicio para interactuar con la API de Spotify, manejando
    automáticamente la autenticación y el refresco de tokens.
    """
    def __init__(self, user):
        self.user = user
        self.sp = None
        self.auth_manager = None
        self.token_info = None
        
        try:
            # Importar aquí para evitar importaciones circulares
            from applications.spotify_api.models import SpotifyUserToken
            
            # Obtener token del usuario
            spotify_token_obj = SpotifyUserToken.objects.filter(user=user).first()
            
            if not spotify_token_obj:
                logger.warning(f"No hay token de Spotify para el usuario {user.username}")
                return

            # Crear auth manager
            self.auth_manager = self.get_auth_manager()
            
            # Verificar y refrescar token si es necesario
            self.token_info = self._refresh_token_if_needed(spotify_token_obj)
            
            if not self.token_info:
                logger.error(f"No se pudo obtener token válido para {user.username}")
                return
            
            # Crear cliente de Spotify con el token
            self.sp = spotipy.Spotify(auth=self.token_info['access_token'])
            
            logger.info(f"SpotifyService inicializado exitosamente para {user.username}")
            
        except Exception as e:
            logger.error(f"Error inicializando SpotifyService para {user.username}: {str(e)}")
            self.sp = None
    
    @staticmethod
    def get_auth_manager():
        """Retorna el manager de autenticación de Spotify."""
        return SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope="streaming user-library-read user-top-read playlist-read-private user-read-recently-played user-read-email user-read-private"
        )
    
    def _refresh_token_if_needed(self, spotify_token_obj):
        """Verifica y refresca el token si es necesario."""
        try:
            from applications.spotify_api.models import SpotifyUserToken
            
            # Construir token_info actual
            current_token_info = {
                'access_token': spotify_token_obj.access_token,
                'refresh_token': spotify_token_obj.refresh_token,
                'expires_at': int(spotify_token_obj.expires_at.timestamp()),
                'scope': spotify_token_obj.scope,
                'token_type': 'Bearer'
            }
            
            # Verificar si el token está expirado (con margen de 60 segundos)
            current_time = int(time.time())
            expires_at = current_token_info['expires_at']
            
            # Si el token expira en menos de 60 segundos, refrescarlo
            if expires_at - current_time < 60:
                logger.info(f"Token expirando para {self.user.username}, refrescando...")
                
                try:
                    # Intentar refrescar el token
                    new_token_info = self.auth_manager.refresh_access_token(
                        current_token_info['refresh_token']
                    )
                    
                    # Actualizar en la base de datos
                    spotify_token_obj.access_token = new_token_info['access_token']
                    
                    # Mantener el refresh token si se devuelve uno nuevo
                    if 'refresh_token' in new_token_info:
                        spotify_token_obj.refresh_token = new_token_info['refresh_token']
                    
                    # Calcular fecha de expiración
                    expires_at_time = timezone.make_aware(
                        datetime.fromtimestamp(new_token_info['expires_at'])
                    )
                    spotify_token_obj.expires_at = expires_at_time
                    
                    if 'scope' in new_token_info:
                        spotify_token_obj.scope = new_token_info['scope']
                    
                    spotify_token_obj.save()
                    logger.info(f"Token refrescado exitosamente para {self.user.username}")
                    
                    return new_token_info
                    
                except Exception as refresh_error:
                    logger.error(f"Error refrescando token para {self.user.username}: {str(refresh_error)}")
                    
                    # Si el refresh token también expiró, marcar como inválido
                    if "Refresh token revoked" in str(refresh_error):
                        spotify_token_obj.delete()
                        logger.warning(f"Refresh token revocado para {self.user.username}")
                        return None
                    
                    # Si hay otro error, intentar con el token actual
                    return current_token_info
            
            # Si el token aún es válido, usarlo
            return current_token_info
            
        except Exception as e:
            logger.error(f"Error en _refresh_token_if_needed para {self.user.username}: {str(e)}")
            return None
    
    def _ensure_valid_client(self):
        """Verifica que el cliente de Spotify sea válido antes de realizar una operación."""
        if not self.sp:
            logger.warning(f"Intento de usar SpotifyService no inicializado para {self.user.username}")
            return False
        
        try:
            # Intentar una operación simple para verificar si el token sigue siendo válido
            # Si no, intentar refrescarlo
            from applications.spotify_api.models import SpotifyUserToken
            spotify_token_obj = SpotifyUserToken.objects.filter(user=self.user).first()
            
            if spotify_token_obj:
                # Refrescar token si es necesario
                new_token_info = self._refresh_token_if_needed(spotify_token_obj)
                
                if new_token_info:
                    # Recrear el cliente de Spotify con el nuevo token
                    self.sp = spotipy.Spotify(auth=new_token_info['access_token'])
                    return True
                else:
                    logger.error(f"No se pudo obtener token válido para {self.user.username}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error en _ensure_valid_client para {self.user.username}: {str(e)}")
            return False
    
    def _safe_api_call(self, method, *args, **kwargs):
        """Wrapper seguro para llamadas a la API de Spotify."""
        try:
            # Verificar que el cliente sea válido
            if not self._ensure_valid_client():
                logger.warning(f"Cliente de Spotify no válido para {self.user.username}")
                return None
            
            if not self.sp:
                logger.warning(f"Cliente de Spotify no disponible para {self.user.username}")
                return None
            
            # Ejecutar el método
            result = method(*args, **kwargs)
            return result
            
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Error de Spotify API para {self.user.username}: {str(e)}")
            
            # Si el error es 401 (token inválido), intentar refrescar
            if e.http_status == 401:
                logger.info(f"Token inválido (401) para {self.user.username}, intentando refrescar...")
                try:
                    # Forzar refresco de token
                    from applications.spotify_api.models import SpotifyUserToken
                    spotify_token_obj = SpotifyUserToken.objects.filter(user=self.user).first()
                    
                    if spotify_token_obj:
                        new_token_info = self._refresh_token_if_needed(spotify_token_obj)
                        if new_token_info:
                            self.sp = spotipy.Spotify(auth=new_token_info['access_token'])
                            # Reintentar la operación
                            return method(*args, **kwargs)
                except Exception as refresh_error:
                    logger.error(f"Error refrescando token después de 401: {str(refresh_error)}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error inesperado en llamada a Spotify API para {self.user.username}: {str(e)}")
            return None
    
    # ========== MÉTODOS PÚBLICOS (con manejo seguro) ==========
    
    def get_user_playlists(self):
        """Obtiene las playlists del usuario."""
        def _get_playlists():
            return self.sp.current_user_playlists(limit=50)
        
        result = self._safe_api_call(_get_playlists)
        if not result:
            return []
        
        try:
            return [{
                'id': pl['id'],
                'name': pl['name'],
                'uri': pl['uri'],
                'image': pl['images'][0]['url'] if pl['images'] else None,
                'owner': pl['owner']['display_name'],
                'tracks': pl['tracks']['total'],
                'type': 'Playlist'
            } for pl in result['items']]
        except Exception as e:
            logger.error(f"Error procesando playlists: {str(e)}")
            return []
    
    def get_user_top_artists(self, limit=10):
        """Obtiene los artistas más escuchados del usuario."""
        def _get_top_artists():
            return self.sp.current_user_top_artists(limit=limit, time_range='medium_term')
        
        result = self._safe_api_call(_get_top_artists)
        if not result:
            return []
        
        try:
            return [{
                'id': artist['id'],
                'name': artist['name'],
                'uri': artist['uri'],
                'image': artist['images'][0]['url'] if artist['images'] else None,
                'genres': artist['genres'],
                'popularity': artist['popularity']
            } for artist in result['items']]
        except Exception:
            return []
    
    def get_user_top_tracks(self, limit=10):
        """Obtiene las canciones más escuchadas del usuario."""
        def _get_top_tracks():
            return self.sp.current_user_top_tracks(limit=limit, time_range='medium_term')
        
        result = self._safe_api_call(_get_top_tracks)
        if not result:
            return []
        
        try:
            return [{
                'id': track['id'],
                'name': track['name'],
                'uri': track['uri'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'duration_ms': track['duration_ms']
            } for track in result['items']]
        except Exception:
            return []
    
    def get_recently_played(self, limit=20):
        """Obtiene las canciones reproducidas recientemente."""
        def _get_recently_played():
            return self.sp.current_user_recently_played(limit=limit)
        
        result = self._safe_api_call(_get_recently_played)
        if not result:
            return []
        
        try:
            return [{
                'id': item['track']['id'],
                'name': item['track']['name'],
                'uri': item['track']['uri'],
                'artist': ', '.join([artist['name'] for artist in item['track']['artists']]),
                'album': item['track']['album']['name'],
                'image': item['track']['album']['images'][0]['url'] if item['track']['album']['images'] else None,
                'played_at': item['played_at']
            } for item in result['items']]
        except Exception:
            return []
        
    def get_user_profile(self):
        """Obtiene el perfil completo del usuario de Spotify."""
        def _get_user_profile():
            return self.sp.current_user()
        
        result = self._safe_api_call(_get_user_profile)
        if not result:
            return None
        
        try:
            return {
                'id': result.get('id'),
                'display_name': result.get('display_name'),
                'email': result.get('email'),
                'country': result.get('country'),
                'followers': result.get('followers', {}).get('total', 0),
                'image': result['images'][0]['url'] if result.get('images') else None,
                'product': result.get('product'),
                'uri': result.get('uri')
            }
        except Exception:
            return None

    def get_artist_details(self, artist_id):
        """Obtiene los detalles principales de un solo artista."""
        def _get_artist_details():
            return self.sp.artist(artist_id)
        
        result = self._safe_api_call(_get_artist_details)
        if not result:
            return None
        
        try:
            return {
                'id': result['id'],
                'name': result['name'],
                'image': result['images'][0]['url'] if result['images'] else None,
                'followers': f"{result['followers']['total']:,}" 
            }
        except Exception as e:
            logger.error(f"Error obteniendo detalles del artista {artist_id}: {e}")
            return None

    def get_artist_top_tracks(self, artist_id, limit=10):
        """Obtiene las canciones más populares de un artista."""
        def _get_artist_top_tracks():
            return self.sp.artist_top_tracks(artist_id, country='US')
        
        result = self._safe_api_call(_get_artist_top_tracks)
        if not result:
            return []
        
        try:
            tracks = []
            for track in result['tracks'][:limit]:
                duration_ms = track['duration_ms']
                total_seconds = int(duration_ms / 1000)
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                formatted_duration = f"{minutes}:{seconds:02d}"
                
                # SE AGREGA POPULARITY Y ARTIST_NAME
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'uri': track['uri'],
                    'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'duration_ms': duration_ms,
                    'duration_formatted': formatted_duration,
                    'artist_name': track['artists'][0]['name'],
                    'album_name': track['album']['name'],
                    'popularity': track.get('popularity', 0)
                })
            return tracks
        except Exception as e:
            logger.error(f"Error obteniendo top tracks del artista {artist_id}: {e}")
            return []

    def get_artist_albums(self, artist_id, limit=20):
        """Obtiene los álbumes y sencillos de un artista."""
        def _get_artist_albums():
            return self.sp.artist_albums(artist_id, album_type='album,single', limit=limit)
        
        result = self._safe_api_call(_get_artist_albums)
        if not result:
            return []
        
        try:
            albums = []
            seen_names = set() 
            for album in result['items']:
                if album['name'].lower() not in seen_names:
                    albums.append({
                        'id': album['id'],
                        'name': album['name'],
                        'image': album['images'][0]['url'] if album['images'] else None,
                        'release_year': album['release_date'][:4],
                        'type': album['album_type']
                    })
                    seen_names.add(album['name'].lower())
            return albums
        except Exception as e:
            logger.error(f"Error obteniendo álbumes del artista {artist_id}: {e}")
            return []
    
    def get_album_details(self, album_id):
        """Obtiene los detalles de un álbum y su lista completa de canciones."""
        def _get_album_details():
            return self.sp.album(album_id)
        
        result = self._safe_api_call(_get_album_details)
        if not result:
            return None
        
        try:
            album_info = {
                'id': result['id'],
                'name': result['name'],
                'artist_name': ', '.join([artist['name'] for artist in result['artists']]),
                'image': result['images'][0]['url'] if result['images'] else None,
                'release_year': result['release_date'][:4],
                'total_tracks': result['total_tracks'],
                'type': result['album_type']
            }
            
            tracks = []
            for track in result['tracks']['items']:
                duration_ms = track['duration_ms']
                total_seconds = int(duration_ms / 1000)
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                formatted_duration = f"{minutes}:{seconds:02d}"

                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'uri': track['uri'],
                    'track_number': track['track_number'],
                    'duration_formatted': formatted_duration
                })
            
            return {'album_info': album_info, 'tracks': tracks}

        except Exception as e:
            logger.error(f"Error obteniendo detalles del álbum {album_id}: {e}")
            return None
        
    def search_spotify(self, query, limit=5):
        """
        Busca en Spotify por canciones, artistas, álbumes y playlists.
        Versión robusta que maneja todos los casos.
        """
        if not query or query.strip() == '':
            return {
                'tracks': [],
                'artists': [],
                'albums': [],
                'playlists': []
            }
        
        def _search_spotify():
            return self.sp.search(
                q=query.strip(), 
                type='track,artist,album,playlist', 
                limit=limit,
                market='CO'
            )
        
        result = self._safe_api_call(_search_spotify)
        if not result:
            return {
                'tracks': [],
                'artists': [],
                'albums': [],
                'playlists': []
            }
        
        try:
            # Inicializar con valores por defecto
            tracks = []
            artists = []
            albums = []
            playlists = []
            
            # Procesar TRACKS
            if 'tracks' in result and isinstance(result['tracks'], dict):
                track_items = result['tracks'].get('items', [])
                
                for t in track_items:
                    try:
                        artist_names = []
                        if 'artists' in t:
                            for artist in t['artists']:
                                if 'name' in artist:
                                    artist_names.append(artist['name'])
                        
                        image_url = None
                        if 'album' in t and 'images' in t['album'] and t['album']['images']:
                            image_url = t['album']['images'][0]['url']
                        
                        duration_ms = t.get('duration_ms', 0)
                        minutes = int(duration_ms / 60000)
                        seconds = int((duration_ms % 60000) / 1000)
                        duration_formatted = f"{minutes}:{seconds:02d}"
                        
                        tracks.append({
                            'id': t.get('id', ''),
                            'name': t.get('name', ''),
                            'uri': t.get('uri', ''),
                            'artist': ', '.join(artist_names),
                            'album': {
                                'id': t['album']['id'],
                                'name': t['album']['name'],
                                'image': (
                                    t['album']['images'][0]['url']
                                    if t['album'].get('images')
                                    else ''
                                )
                            },
                            'image': image_url,
                            'duration_formatted': duration_formatted,
                            'duration_ms': duration_ms
                        })
                    except Exception as e:
                        logger.debug(f"Error procesando track: {e}")
                        continue
            
            # Procesar ARTISTS
            if 'artists' in result and isinstance(result['artists'], dict):
                artist_items = result['artists'].get('items', [])
                
                for a in artist_items:
                    try:
                        image_url = None
                        if 'images' in a and a['images']:
                            image_url = a['images'][0]['url']
                        
                        artists.append({
                            'id': a.get('id', ''),
                            'name': a.get('name', ''),
                            'uri': a.get('uri', ''),
                            'image': image_url
                        })
                    except Exception as e:
                        logger.debug(f"Error procesando artist: {e}")
                        continue
            
            # Procesar ALBUMS
            if 'albums' in result and isinstance(result['albums'], dict):
                album_items = result['albums'].get('items', [])                
                for a in album_items:
                    try:
                        image_url = None
                        if 'images' in a and a['images']:
                            image_url = a['images'][0]['url']
                        
                        release_year = ''
                        if 'release_date' in a:
                            release_year = str(a['release_date'])[:4]
                        
                        # Extraer artistas del álbum
                        album_artists = []
                        for artist in a.get('artists', []):
                            album_artists.append({
                                'id': artist.get('id', ''),
                                'name': artist.get('name', '')
                            })
                        
                        albums.append({
                            'id': a.get('id', ''),
                            'name': a.get('name', ''),
                            'artists': album_artists,
                            'image': image_url,
                            'release_year': release_year,
                            'total_tracks': a.get('total_tracks', 0)
                        })
                    except Exception as e:
                        logger.debug(f"Error procesando album: {e}")
                        continue
            
            # Procesar PLAYLISTS
            if 'playlists' in result and isinstance(result['playlists'], dict):
                playlist_items = result['playlists'].get('items', [])
                
                for p in playlist_items:
                    try:
                        image_url = None
                        if 'images' in p and p['images']:
                            image_url = p['images'][0]['url']
                        
                        owner_name = ''
                        if 'owner' in p and 'display_name' in p['owner']:
                            owner_name = p['owner']['display_name']
                        
                        total_tracks = 0
                        if 'tracks' in p and 'total' in p['tracks']:
                            total_tracks = p['tracks']['total']
                        
                        playlists.append({
                            'id': p.get('id', ''),
                            'name': p.get('name', ''),
                            'uri': p.get('uri', ''),
                            'image': image_url,
                            'owner': owner_name,
                            'tracks': total_tracks
                        })
                    except Exception as e:
                        logger.debug(f"Error procesando playlist: {e}")
                        continue
            
            
            return {
                'tracks': tracks,
                'artists': artists,
                'albums': albums,
                'playlists': playlists
            }
            
        except Exception as e:
            logger.error(f"Error procesando resultados de búsqueda: {str(e)}")
            return {
                'tracks': [],
                'artists': [],
                'albums': [],
                'playlists': []
            }
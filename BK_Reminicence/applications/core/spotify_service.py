import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from django.utils import timezone
from datetime import datetime

class SpotifyService:
    """
    Servicio para interactuar con la API de Spotify, manejando
    automáticamente la autenticación y el refresco de tokens.
    """
    def __init__(self, user):
        self.user = user
        self.sp = None
        
        try:
            from applications.spotify_api.models import SpotifyUserToken
            spotify_token_obj = SpotifyUserToken.objects.filter(user=user).first()
            
            if not spotify_token_obj:
                return

            auth_manager = self.get_auth_manager()
            
            token_info = {
                'access_token': spotify_token_obj.access_token,
                'refresh_token': spotify_token_obj.refresh_token,
                'expires_at': int(spotify_token_obj.expires_at.timestamp()),
                'scope': spotify_token_obj.scope
            }

            if auth_manager.is_token_expired(token_info):
                new_token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
                
                spotify_token_obj.access_token = new_token_info['access_token']
                spotify_token_obj.refresh_token = new_token_info.get('refresh_token', spotify_token_obj.refresh_token)
                spotify_token_obj.expires_at = timezone.make_aware(datetime.fromtimestamp(new_token_info['expires_at']))
                spotify_token_obj.scope = new_token_info['scope']
                spotify_token_obj.save()
                
                token_info = new_token_info

            self.sp = spotipy.Spotify(auth=token_info['access_token'])

        except Exception:
            # En caso de error, self.sp seguirá siendo None, y los métodos
            # que lo usan devolverán listas vacías o None de forma segura.
            pass
    
    @staticmethod
    def get_auth_manager():
        """Retorna el manager de autenticación de Spotify."""
        return SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope="streaming user-library-read user-top-read playlist-read-private user-read-recently-played user-read-email user-read-private"
        )
    
    def get_user_playlists(self):
        """Obtiene las playlists del usuario."""
        if not self.sp:
            return []
        
        try:
            playlists = self.sp.current_user_playlists(limit=50)
            return [{
                'id': pl['id'],
                'name': pl['name'],
                'uri': pl['uri'],
                'image': pl['images'][0]['url'] if pl['images'] else None,
                'owner': pl['owner']['display_name'],
                'tracks': pl['tracks']['total'],
                'type': 'Playlist'
            } for pl in playlists['items']]
        except Exception:
            return []
    
    def get_user_top_artists(self, limit=10):
        """Obtiene los artistas más escuchados del usuario."""
        if not self.sp:
            return []
        
        try:
            artists = self.sp.current_user_top_artists(limit=limit, time_range='medium_term')
            return [{
                'id': artist['id'],
                'name': artist['name'],
                'uri': artist['uri'],
                'image': artist['images'][0]['url'] if artist['images'] else None,
                'genres': artist['genres'],
                'popularity': artist['popularity']
            } for artist in artists['items']]
        except Exception:
            return []
    
    def get_user_top_tracks(self, limit=10):
        """Obtiene las canciones más escuchadas del usuario."""
        if not self.sp:
            return []
        
        try:
            tracks = self.sp.current_user_top_tracks(limit=limit, time_range='medium_term')
            return [{
                'id': track['id'],
                'name': track['name'],
                'uri': track['uri'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'duration_ms': track['duration_ms']
            } for track in tracks['items']]
        except Exception:
            return []
    
    def get_recently_played(self, limit=20):
        """Obtiene las canciones reproducidas recientemente."""
        if not self.sp:
            return []
        
        try:
            recent = self.sp.current_user_recently_played(limit=limit)
            return [{
                'id': item['track']['id'],
                'name': item['track']['name'],
                'uri': item['track']['uri'],
                'artist': ', '.join([artist['name'] for artist in item['track']['artists']]),
                'album': item['track']['album']['name'],
                'image': item['track']['album']['images'][0]['url'] if item['track']['album']['images'] else None,
                'played_at': item['played_at']
            } for item in recent['items']]
        except Exception:
            return []
        
    def get_user_profile(self):
        """Obtiene el perfil completo del usuario de Spotify."""
        if not self.sp:
            return None
        
        try:
            user_profile = self.sp.current_user()
            return {
                'id': user_profile.get('id'),
                'display_name': user_profile.get('display_name'),
                'email': user_profile.get('email'),
                'country': user_profile.get('country'),
                'followers': user_profile.get('followers', {}).get('total', 0),
                'image': user_profile.get('images')[0]['url'] if user_profile.get('images') else None,
                'product': user_profile.get('product'),
                'uri': user_profile.get('uri')
            }
        except Exception:
            return None

    def get_artist_details(self, artist_id):
        """Obtiene los detalles principales de un solo artista."""
        if not self.sp:
            return None
        
        try:
            artist_data = self.sp.artist(artist_id)
            return {
                'id': artist_data['id'],
                'name': artist_data['name'],
                'image': artist_data['images'][0]['url'] if artist_data['images'] else None,
                'followers': f"{artist_data['followers']['total']:,}" 
            }
        except Exception as e:
            print(f"Error obteniendo detalles del artista {artist_id}: {e}")
            return None

    def get_artist_top_tracks(self, artist_id, limit=10):
            """Obtiene las canciones más populares de un artista."""
            if not self.sp:
                return []
            
            try:
                top_tracks_data = self.sp.artist_top_tracks(artist_id, country='US')
                
                tracks = []
                for track in top_tracks_data['tracks'][:limit]:
                    
                    duration_ms = track['duration_ms']
                    total_seconds = int(duration_ms / 1000)
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    formatted_duration = f"{minutes}:{seconds:02d}"
                    
                    tracks.append({
                        'id': track['id'],
                        'name': track['name'],
                        'uri': track['uri'],
                        'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                        'duration_ms': duration_ms, # Mantenemos el original por si acaso
                        'duration_formatted': formatted_duration # Añadimos el nuevo campo formateado
                    })
                return tracks
            except Exception as e:
                print(f"Error obteniendo top tracks del artista {artist_id}: {e}")
                return []

    def get_artist_albums(self, artist_id, limit=20):
        """Obtiene los álbumes y sencillos de un artista."""
        if not self.sp:
            return []
        
        try:
            albums_data = self.sp.artist_albums(artist_id, album_type='album,single', limit=limit)
            
            albums = []
            seen_names = set() 
            for album in albums_data['items']:
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
            print(f"Error obteniendo álbumes del artista {artist_id}: {e}")
            return []
    
    def get_album_details(self, album_id):
        """
        Obtiene los detalles de un álbum y su lista completa de canciones.
        """
        if not self.sp:
            return None
        
        try:
            album_data = self.sp.album(album_id)

            # 1. Formatear la información principal del álbum
            album_info = {
                'id': album_data['id'],
                'name': album_data['name'],
                'artist_name': ', '.join([artist['name'] for artist in album_data['artists']]),
                'image': album_data['images'][0]['url'] if album_data['images'] else None,
                'release_year': album_data['release_date'][:4],
                'total_tracks': album_data['total_tracks'],
                'type': album_data['album_type']
            }
            
            # 2. Formatear la lista de canciones del álbum
            tracks = []
            for track in album_data['tracks']['items']:
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
            print(f"Error obteniendo detalles del álbum {album_id}: {e}")
            return None
        
    def search_spotify(self, query, limit=5):
        """
        Busca en Spotify por canciones, artistas, álbumes y playlists.
        """
        if not self.sp or not query:
            return {}
        
        try:
            results = self.sp.search(q=query, type='track,artist,album,playlist', limit=limit)
            
            # Formatear Canciones
            tracks = [{
                'id': t['id'], 'name': t['name'], 'uri': t['uri'],
                'artist': ', '.join([a['name'] for a in t['artists']]),
                'image': t['album']['images'][0]['url'] if t['album']['images'] else None,
                'duration_formatted': f"{int(t['duration_ms']/60000)}:{(int(t['duration_ms']/1000)%60):02d}"
            } for t in results['tracks']['items']]

            # Formatear Artistas
            artists = [{
                'id': a['id'], 'name': a['name'], 'uri': a['uri'],
                'image': a['images'][0]['url'] if a['images'] else None
            } for a in results['artists']['items']]

            # Formatear Álbumes
            albums = [{
                'id': a['id'], 'name': a['name'],
                'image': a['images'][0]['url'] if a['images'] else None,
                'release_year': a['release_date'][:4]
            } for a in results['albums']['items']]

            return {
                'tracks': tracks,
                'artists': artists,
                'albums': albums,
            }
        except Exception as e:
            print(f"Error en la búsqueda de Spotify: {e}")
            return {}
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from django.utils import timezone
from datetime import datetime

class SpotifyService:
    def __init__(self, user):
        """
        Inicializa el servicio de Spotify, manejando automáticamente
        la expiración y el refresco del token.
        """
        self.user = user
        self.sp = None
        
        try:
            from applications.spotify_api.models import SpotifyUserToken
            spotify_token_obj = SpotifyUserToken.objects.filter(user=user).first()
            
            if not spotify_token_obj:
                print(f"[INIT] No se encontró un SpotifyUserToken para {user.username}")
                return

            # 1. Crear el gestor de autenticación que sabe cómo refrescar tokens
            auth_manager = self.get_auth_manager()
            
            # 2. Cargar la información del token desde la BD en un formato que spotipy entienda
            token_info = {
                'access_token': spotify_token_obj.access_token,
                'refresh_token': spotify_token_obj.refresh_token,
                'expires_at': int(spotify_token_obj.expires_at.timestamp()),
                'scope': spotify_token_obj.scope
            }

            # 3. Verificar si el token ha expirado
            if auth_manager.is_token_expired(token_info):
                print(f"[REFRESH] El token para {user.username} ha expirado. Refrescando...")
                
                # 4. Usar el refresh_token para obtener un nuevo access_token
                new_token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
                
                # 5. ¡CRUCIAL! Guardar el NUEVO token en la base de datos para el futuro
                spotify_token_obj.access_token = new_token_info['access_token']
                # Spotify no siempre devuelve un nuevo refresh token, así que conservamos el viejo si no viene uno nuevo
                spotify_token_obj.refresh_token = new_token_info.get('refresh_token', spotify_token_obj.refresh_token)
                spotify_token_obj.expires_at = timezone.make_aware(datetime.fromtimestamp(new_token_info['expires_at']))
                spotify_token_obj.scope = new_token_info['scope']
                spotify_token_obj.save()
                
                print(f"[REFRESH] Token refrescado y guardado correctamente.")
                # Usar el token recién refrescado para esta sesión
                token_info = new_token_info

            # 6. Inicializar el cliente de Spotipy con un token garantizado de ser válido
            self.sp = spotipy.Spotify(auth=token_info['access_token'])
            print(f"[INIT] SpotifyService inicializado correctamente para {user.username}")

        except Exception as e:
            import traceback
            print(f"[INIT-ERROR] Error al inicializar SpotifyService: {e}")
            traceback.print_exc()
    
    @staticmethod
    def get_auth_manager():
        """Retorna el manager de autenticación de Spotify"""
        return SpotifyOAuth(
            client_id=settings.SPOTIFY_CLIENT_ID,
            client_secret=settings.SPOTIFY_CLIENT_SECRET,
            redirect_uri=settings.SPOTIFY_REDIRECT_URI,
            scope="user-library-read user-top-read playlist-read-private user-read-recently-played"
        )
    
    def get_user_playlists(self):
        """Obtiene las playlists del usuario"""
        print(f"[PLAYLISTS] Llamado. sp existe: {self.sp is not None}")
        
        if not self.sp:
            print("[PLAYLISTS] No hay cliente de Spotify inicializado")
            return []
        
        try:
            print("[PLAYLISTS] Obteniendo playlists de Spotify...")
            playlists = self.sp.current_user_playlists(limit=50)
            print(f"[PLAYLISTS] Playlists obtenidas: {len(playlists['items'])}")
            
            result = [{
                'id': pl['id'],
                'name': pl['name'],
                'image': pl['images'][0]['url'] if pl['images'] else None,
                'owner': pl['owner']['display_name'],
                'tracks': pl['tracks']['total'],
                'type': 'Playlist'
            } for pl in playlists['items']]
            
            print(f"[PLAYLISTS] Playlists procesadas: {len(result)}")
            return result
        except Exception as e:
            print(f"[PLAYLISTS] Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_user_top_artists(self, limit=10):
        """Obtiene los artistas más escuchados del usuario"""
        if not self.sp:
            return []
        
        try:
            artists = self.sp.current_user_top_artists(limit=limit, time_range='medium_term')
            return [{
                'id': artist['id'],
                'name': artist['name'],
                'image': artist['images'][0]['url'] if artist['images'] else None,
                'genres': artist['genres'],
                'popularity': artist['popularity']
            } for artist in artists['items']]
        except Exception as e:
            print(f"Error al obtener artistas: {e}")
            return []
    
    def get_user_top_tracks(self, limit=10):
        """Obtiene las canciones más escuchadas del usuario"""
        if not self.sp:
            return []
        
        try:
            tracks = self.sp.current_user_top_tracks(limit=limit, time_range='medium_term')
            return [{
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'duration_ms': track['duration_ms']
            } for track in tracks['items']]
        except Exception as e:
            print(f"Error al obtener canciones: {e}")
            return []
    
    def get_recently_played(self, limit=20):
        """Obtiene las canciones reproducidas recientemente"""
        if not self.sp:
            return []
        
        try:
            recent = self.sp.current_user_recently_played(limit=limit)
            return [{
                'name': item['track']['name'],
                'artist': ', '.join([artist['name'] for artist in item['track']['artists']]),
                'album': item['track']['album']['name'],
                'image': item['track']['album']['images'][0]['url'] if item['track']['album']['images'] else None,
                'played_at': item['played_at']
            } for item in recent['items']]
        except Exception as e:
            print(f"Error al obtener reproducidos recientemente: {e}")
            return []
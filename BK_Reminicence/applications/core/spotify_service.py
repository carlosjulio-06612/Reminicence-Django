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
            scope="user-library-read user-top-read playlist-read-private user-read-recently-played user-read-email user-read-private"
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
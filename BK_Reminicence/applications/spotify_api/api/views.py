import urllib.parse
import requests
from django.conf import settings
from django.contrib.auth import login
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes

from ..models import SpotifyUserToken
from ..utils import (
    get_spotify_user_profile,
    find_or_create_user_from_spotify,
    save_spotify_tokens,
    get_user_spotify_token,
    refresh_spotify_token
)
from applications.core.spotify_service import SpotifyService
from .serializers import (
    SpotifyAuthURLSerializer,
    SpotifyCallbackSerializer,
    SpotifyUserTokenSerializer,
    PlaybackStateSerializer,
    PlaybackControlSerializer,
    SeekTrackSerializer,
    ShuffleSerializer,
    RepeatSerializer,
    SpotifyErrorSerializer
)


class SpotifyAuthURLView(APIView):
    """
    GET: Obtener URL de autorización de Spotify
    
    Genera la URL para que el usuario autorice la aplicación en Spotify.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        scope = (
            'user-read-private user-read-email '
            'playlist-read-private user-library-read '
            'user-top-read '
            'user-read-recently-played '
            'user-read-playback-state '
            'user-modify-playback-state '
            'streaming'
        )
        
        params = {
            'client_id': settings.SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
            'scope': scope,
        }
        
        auth_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
        
        serializer = SpotifyAuthURLSerializer({'auth_url': auth_url})
        return Response(serializer.data)


class SpotifyCallbackView(APIView):
    """
    POST: Procesar callback de autorización de Spotify
    
    Recibe el código de autorización y lo intercambia por tokens.
    Puede crear un nuevo usuario o vincular Spotify a usuario existente.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SpotifyCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data.get('code')
        
        # Intercambiar código por tokens
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
                'client_id': settings.SPOTIFY_CLIENT_ID,
                'client_secret': settings.SPOTIFY_CLIENT_SECRET,
            }
        )
        
        if response.status_code != 200:
            return Response(
                {'error': 'Error al obtener tokens de Spotify'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token_data = response.json()
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        expires_in = token_data['expires_in']
        scope = token_data['scope']
        
        # Obtener perfil del usuario
        spotify_profile = get_spotify_user_profile(access_token)
        
        if not spotify_profile:
            return Response(
                {'error': 'No se pudo obtener tu perfil de Spotify'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        spotify_user_id = spotify_profile['id']
        
        # Verificar si el usuario ya está autenticado
        if request.user.is_authenticated:
            # Modo: Vincular Spotify a cuenta existente
            existing_token = SpotifyUserToken.objects.filter(
                spotify_user_id=spotify_user_id
            ).first()
            
            if existing_token and existing_token.user != request.user:
                return Response(
                    {
                        'error': f'Esta cuenta de Spotify ya está vinculada al usuario "{existing_token.user.username}"'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            save_spotify_tokens(
                request.user,
                access_token,
                refresh_token,
                expires_in,
                scope,
                spotify_user_id
            )
            
            return Response({
                'message': 'Tu cuenta de Spotify ha sido vinculada exitosamente',
                'spotify_linked': True
            })
        
        else:
            # Modo: Login social con Spotify
            existing_token = SpotifyUserToken.objects.filter(
                spotify_user_id=spotify_user_id
            ).first()
            
            if existing_token:
                # Usuario ya existe, hacer login
                user = existing_token.user
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Actualizar tokens
                save_spotify_tokens(
                    user,
                    access_token,
                    refresh_token,
                    expires_in,
                    scope,
                    spotify_user_id
                )
                
                # Generar JWT
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(user)
                
                from applications.users.api.serializers import UserSerializer
                
                return Response({
                    'message': f'¡Bienvenido de vuelta, {user.username}!',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'spotify_linked': True
                })
            
            else:
                # Crear nuevo usuario
                user, created = find_or_create_user_from_spotify(spotify_profile)
                save_spotify_tokens(
                    user,
                    access_token,
                    refresh_token,
                    expires_in,
                    scope,
                    spotify_user_id
                )
                
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Generar JWT
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(user)
                
                from applications.users.api.serializers import UserSerializer
                
                return Response({
                    'message': 'Cuenta creada exitosamente con Spotify' if created else 'Cuenta vinculada exitosamente',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'spotify_linked': True
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SpotifyStatusView(APIView):
    """
    GET: Verificar si el usuario tiene Spotify vinculado
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            token = SpotifyUserToken.objects.get(user=request.user)
            serializer = SpotifyUserTokenSerializer(token)
            return Response({
                'spotify_linked': True,
                'spotify_user_id': serializer.data['spotify_user_id'],
                'expires_at': serializer.data['expires_at']
            })
        except SpotifyUserToken.DoesNotExist:
            return Response({
                'spotify_linked': False
            })


# ===================================================================
# ===== CONTROL DEL REPRODUCTOR =====================================
# ===================================================================

class CurrentPlaybackView(APIView):
    """
    GET: Obtener estado actual de reproducción
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            current_playback = spotify_service.sp.current_playback()
            
            if current_playback and current_playback.get('item'):
                data = {
                    'is_playing': current_playback['is_playing'],
                    'progress_ms': current_playback['progress_ms'],
                    'shuffle_state': current_playback.get('shuffle_state', False),
                    'repeat_state': current_playback.get('repeat_state', 'off'),
                    'item': {
                        'id': current_playback['item']['id'],
                        'name': current_playback['item']['name'],
                        'duration_ms': current_playback['item']['duration_ms'],
                        'album': {
                            'name': current_playback['item']['album']['name'],
                            'images': current_playback['item']['album']['images']
                        },
                        'artists': [
                            {'name': a['name'], 'id': a['id']} 
                            for a in current_playback['item']['artists']
                        ]
                    }
                }
                serializer = PlaybackStateSerializer(data)
                return Response(serializer.data)
            else:
                return Response({}, status=status.HTTP_204_NO_CONTENT)
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlaySpotifyURIView(APIView):
    """
    POST: Iniciar reproducción de una canción/playlist/álbum
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            serializer = PlaybackControlSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            device_id = serializer.validated_data.get('device_id')
            uri_to_play = serializer.validated_data.get('uri')
            context_uri = serializer.validated_data.get('context_uri')
            uris_list = serializer.validated_data.get('uris')
            
            if uris_list:
                spotify_service.sp.start_playback(uris=uris_list, device_id=device_id)
            elif context_uri:
                spotify_service.sp.start_playback(
                    context_uri=context_uri,
                    offset={'uri': uri_to_play} if uri_to_play else None,
                    device_id=device_id
                )
            elif uri_to_play:
                if 'track' in uri_to_play:
                    spotify_service.sp.start_playback(uris=[uri_to_play], device_id=device_id)
                else:
                    spotify_service.sp.start_playback(context_uri=uri_to_play, device_id=device_id)
            else:
                spotify_service.sp.start_playback(device_id=device_id)
            
            return Response({'status': 'success', 'message': 'Reproducción iniciada'})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PausePlaybackView(APIView):
    """
    POST: Pausar reproducción
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            device_id = request.data.get('device_id')
            spotify_service.sp.pause_playback(device_id=device_id)
            
            return Response({'status': 'success', 'message': 'Reproducción pausada'})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NextTrackView(APIView):
    """
    POST: Saltar a siguiente canción
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            device_id = request.data.get('device_id')
            spotify_service.sp.next_track(device_id=device_id)
            
            return Response({'status': 'success', 'message': 'Siguiente canción'})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PreviousTrackView(APIView):
    """
    POST: Volver a canción anterior
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            device_id = request.data.get('device_id')
            spotify_service.sp.previous_track(device_id=device_id)
            
            return Response({'status': 'success', 'message': 'Canción anterior'})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SeekTrackView(APIView):
    """
    POST: Saltar a posición específica en la canción
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            serializer = SeekTrackSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            position_ms = serializer.validated_data['position_ms']
            device_id = serializer.validated_data.get('device_id')
            
            spotify_service.sp.seek_track(position_ms, device_id=device_id)
            
            return Response({'status': 'success', 'message': f'Posición cambiada a {position_ms}ms'})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ShufflePlaybackView(APIView):
    """
    POST: Activar/desactivar modo aleatorio
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            serializer = ShuffleSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            shuffle_state = serializer.validated_data['state']
            device_id = serializer.validated_data.get('device_id')
            
            spotify_service.sp.shuffle(shuffle_state, device_id=device_id)
            
            return Response({
                'status': 'success',
                'message': f'Modo aleatorio {"activado" if shuffle_state else "desactivado"}'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RepeatPlaybackView(APIView):
    """
    POST: Cambiar modo de repetición (off/context/track)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            spotify_service = SpotifyService(request.user)
            if not spotify_service.sp:
                return Response(
                    {'error': 'Spotify no está conectado'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            serializer = RepeatSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            repeat_state = serializer.validated_data['state']
            device_id = serializer.validated_data.get('device_id')
            
            spotify_service.sp.repeat(repeat_state, device_id=device_id)
            
            return Response({
                'status': 'success',
                'message': f'Modo repetición: {repeat_state}'
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
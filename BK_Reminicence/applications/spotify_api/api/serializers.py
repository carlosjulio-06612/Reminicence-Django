from rest_framework import serializers
from ..models import SpotifyUserToken


class SpotifyUserTokenSerializer(serializers.ModelSerializer):
    """Serializer para tokens de Spotify"""
    
    class Meta:
        model = SpotifyUserToken
        fields = [
            'token_id',
            'access_token',
            'refresh_token',
            'expires_at',
            'scope',
            'spotify_user_id',
        ]
        read_only_fields = ['token_id']
        extra_kwargs = {
            'access_token': {'write_only': True},
            'refresh_token': {'write_only': True},
        }


class SpotifyAuthURLSerializer(serializers.Serializer):
    """Serializer para respuesta de URL de autenticación"""
    auth_url = serializers.URLField()


class SpotifyCallbackSerializer(serializers.Serializer):
    """Serializer para el callback de Spotify"""
    code = serializers.CharField(required=True)
    state = serializers.CharField(required=False, allow_blank=True)


class SpotifyProfileSerializer(serializers.Serializer):
    """Serializer para perfil de usuario de Spotify"""
    id = serializers.CharField()
    display_name = serializers.CharField(allow_blank=True, allow_null=True)
    email = serializers.EmailField()
    images = serializers.ListField(child=serializers.DictField(), required=False)
    followers = serializers.DictField(required=False)
    country = serializers.CharField(required=False)


class PlaybackStateSerializer(serializers.Serializer):
    """Serializer para estado de reproducción actual"""
    is_playing = serializers.BooleanField()
    progress_ms = serializers.IntegerField()
    shuffle_state = serializers.BooleanField()
    repeat_state = serializers.CharField()
    item = serializers.DictField()


class PlaybackControlSerializer(serializers.Serializer):
    """Serializer para controlar la reproducción"""
    device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    uri = serializers.CharField(required=False, allow_blank=True)
    context_uri = serializers.CharField(required=False, allow_blank=True)
    uris = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class SeekTrackSerializer(serializers.Serializer):
    """Serializer para saltar a posición en la canción"""
    position_ms = serializers.IntegerField(min_value=0)
    device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ShuffleSerializer(serializers.Serializer):
    """Serializer para modo shuffle"""
    state = serializers.BooleanField()
    device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class RepeatSerializer(serializers.Serializer):
    """Serializer para modo repeat"""
    state = serializers.ChoiceField(choices=['off', 'context', 'track'])
    device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class SpotifyErrorSerializer(serializers.Serializer):
    """Serializer para errores de Spotify"""
    error = serializers.CharField()
    message = serializers.CharField(required=False)
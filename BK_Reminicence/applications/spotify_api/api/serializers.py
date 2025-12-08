from rest_framework import serializers
from django.contrib.auth.models import User
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

class UserSerializer(serializers.ModelSerializer):
    """Serializer completo del usuario con información de Spotify"""
    spotify_linked = serializers.SerializerMethodField()
    spotify_user_id = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'spotify_linked',
            'spotify_user_id'
        ]
        read_only_fields = ['id', 'date_joined', 'spotify_linked', 'spotify_user_id']
    
    def get_spotify_linked(self, obj):
        """Verifica si el usuario tiene Spotify vinculado"""
        return SpotifyUserToken.objects.filter(user=obj).exists()
    
    def get_spotify_user_id(self, obj):
        """Obtiene el ID de usuario de Spotify si está vinculado"""
        try:
            token = SpotifyUserToken.objects.get(user=obj)
            return token.spotify_user_id
        except SpotifyUserToken.DoesNotExist:
            return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar información del usuario"""
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def validate_username(self, value):
        """Validar que el username no esté en uso por otro usuario"""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError(
                "Este nombre de usuario ya está en uso."
            )
        return value
    
    def validate_email(self, value):
        """Validar que el email no esté en uso por otro usuario"""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError(
                "Este correo electrónico ya está en uso."
            )
        return value


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de nuevos usuarios"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'first_name', 'last_name']
    
    def validate(self, data):
        """Validar que las contraseñas coincidan"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        return data
    
    def create(self, validated_data):
        """Crear nuevo usuario con contraseña encriptada"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambiar contraseña"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    
    def validate_old_password(self, value):
        """Validar que la contraseña actual sea correcta"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Contraseña actual incorrecta.')
        return value
    
    def save(self):
        """Guardar la nueva contraseña"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """Serializer personalizado para JWT con información adicional"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from rest_framework_simplejwt.tokens import RefreshToken
        
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError(
                'Credenciales inválidas. Verifica tu usuario y contraseña.'
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                'Tu cuenta está desactivada. Contacta al administrador.'
            )
        
        refresh = RefreshToken.for_user(user)
        
        return {
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }

    
class VolumeControlSerializer(serializers.Serializer):
    """Serializer para controlar el volumen"""
    volume_percent = serializers.IntegerField(min_value=0, max_value=100)
    device_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
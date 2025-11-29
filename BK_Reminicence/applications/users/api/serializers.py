from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from applications.spotify_api.models import SpotifyUserToken


class UserSerializer(serializers.ModelSerializer):
    """Serializer para información básica del usuario"""
    spotify_linked = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'date_joined', 'spotify_linked']
        read_only_fields = ['id', 'date_joined']
    
    def get_spotify_linked(self, obj):
        return SpotifyUserToken.objects.filter(user=obj).exists()


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de nuevos usuarios"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'},
        label="Confirmar contraseña"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 
                  'first_name', 'last_name']
    
    def validate_email(self, value):
        """Validar que el email no exista"""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con este correo electrónico."
            )
        return value.lower()
    
    def validate_username(self, value):
        """Validar que el username no exista"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Este nombre de usuario ya está en uso."
            )
        return value
    
    def validate(self, attrs):
        """Validar que las contraseñas coincidan"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Las contraseñas no coinciden."
            })
        return attrs
    
    def create(self, validated_data):
        """Crear usuario"""
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar perfil de usuario"""
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
    
    def validate_email(self, value):
        """Validar email (excepto el del usuario actual)"""
        user = self.context['request'].user
        if User.objects.filter(email=value.lower()).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                "Este correo ya está en uso por otra cuenta."
            )
        return value.lower()
    
    def validate_username(self, value):
        """Validar username (excepto el del usuario actual)"""
        user = self.context['request'].user
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                "Este nombre de usuario ya está en uso."
            )
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambio de contraseña"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        """Validar que la contraseña antigua sea correcta"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Contraseña incorrecta.")
        return value
    
    def validate(self, attrs):
        """Validar que las nuevas contraseñas coincidan"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Las contraseñas no coinciden."
            })
        return attrs
    
    def save(self, **kwargs):
        """Cambiar la contraseña"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado para JWT con información adicional"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar claims personalizados
        token['username'] = user.username
        token['email'] = user.email
        token['spotify_linked'] = SpotifyUserToken.objects.filter(user=user).exists()
        
        return token
    
    def validate(self, attrs):
        """Validación personalizada"""
        data = super().validate(attrs)
        
        # Agregar información del usuario a la respuesta
        data['user'] = UserSerializer(self.user).data
        
        return data
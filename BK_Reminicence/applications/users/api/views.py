from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from applications.spotify_api.models import SpotifyUserToken
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from rest_framework.views import APIView

from .serializers import (
    UserSerializer,
    UserRegisterSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista personalizada para obtener tokens JWT"""
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios
    
    list: Listar usuarios (solo admin)
    create: Registrar nuevo usuario (público)
    retrieve: Ver detalle de usuario
    update: Actualizar usuario
    partial_update: Actualizar parcialmente usuario
    destroy: Eliminar cuenta
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = []
    
    def get_permissions(self):
        """Permisos dinámicos según la acción"""
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        """Serializer dinámico según la acción"""
        if self.action == 'create':
            return UserRegisterSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def create(self, request, *args, **kwargs):
        """Registrar nuevo usuario"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generar tokens para el nuevo usuario
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': f'¡Cuenta creada para {user.username}!',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener información del usuario actual"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Actualizar perfil del usuario actual"""
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': '¡Tu perfil ha sido actualizado con éxito!',
            'user': UserSerializer(request.user).data
        })
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Cambiar contraseña del usuario actual"""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': '¡Tu contraseña ha sido cambiada exitosamente!'
        })
    
    @action(detail=False, methods=['delete'])
    def delete_account(self, request):
        """Eliminar cuenta del usuario actual"""
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Se requiere la contraseña para eliminar la cuenta.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not request.user.check_password(password):
            return Response(
                {'error': 'Contraseña incorrecta.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = request.user.username
        request.user.delete()
        
        return Response({
            'message': f'La cuenta de {username} ha sido eliminada.'
        }, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def unlink_spotify(self, request):
        """Desvincular cuenta de Spotify"""
        try:
            token = SpotifyUserToken.objects.get(user=request.user)
            token.delete()
            return Response({
                'message': 'Tu cuenta de Spotify ha sido desvinculada correctamente.'
            })
        except SpotifyUserToken.DoesNotExist:
            return Response(
                {'error': 'Tu cuenta no estaba vinculada a Spotify.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
class PasswordResetRequestView(APIView):
    """
    POST: Recibe email y envía enlace de recuperación.
    Publico (AllowAny)
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Generar tokens
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        # URL DEL FRONTEND (REACT)
        # Asegúrate de que coincida con donde corre tu React
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        reset_link = f"{frontend_url}/password-reset/confirm/{uid}/{token}"
        
        # Preparar Email
        subject = "Restablecer contraseña - Reminiscence"
        
        # Puedes usar un template HTML o texto plano
        message = f"""
        Hola {user.username},
        
        Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace:
        
        {reset_link}
        
        Si no fuiste tú, ignora este mensaje.
        """
        
        # Enviar
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER, # Remitente
                [email],
                fail_silently=False,
            )
            return Response({'message': 'Se ha enviado un correo con las instrucciones.'})
        except Exception as e:
            return Response(
                {'error': 'Error al enviar el correo. Intenta más tarde.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetConfirmView(APIView):
    """
    POST: Recibe uid, token y nueva contraseña para cambiarla.
    Publico (AllowAny)
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({'message': 'Contraseña restablecida exitosamente.'})
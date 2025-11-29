"""
Manejo personalizado de excepciones para toda la API
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Maneja excepciones de forma consistente en toda la API.
    
    Estructura de respuesta estandarizada:
    {
        "error": true,
        "message": "Mensaje descriptivo del error",
        "details": {...},  # Detalles adicionales si existen
        "status_code": 400
    }
    """
    # Obtener la respuesta estándar de DRF
    response = exception_handler(exc, context)
    
    # Si DRF manejó la excepción
    if response is not None:
        custom_response = {
            'error': True,
            'message': get_error_message(exc),
            'status_code': response.status_code
        }
        
        # Agregar detalles si existen
        if response.data:
            custom_response['details'] = response.data
        
        response.data = custom_response
        
        # Log de errores 500
        if response.status_code >= 500:
            logger.error(
                f"Server Error: {exc}",
                exc_info=True,
                extra={'context': context}
            )
        
        return response
    
    # Manejar excepciones no capturadas por DRF
    
    # ValidationError de Django
    if isinstance(exc, DjangoValidationError):
        return Response({
            'error': True,
            'message': 'Error de validación',
            'details': exc.message_dict if hasattr(exc, 'message_dict') else str(exc),
            'status_code': status.HTTP_400_BAD_REQUEST
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Http404
    if isinstance(exc, Http404):
        return Response({
            'error': True,
            'message': 'Recurso no encontrado',
            'status_code': status.HTTP_404_NOT_FOUND
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Error genérico del servidor
    logger.error(
        f"Unhandled Exception: {exc}",
        exc_info=True,
        extra={'context': context}
    )
    
    return Response({
        'error': True,
        'message': 'Error interno del servidor',
        'details': str(exc) if settings.DEBUG else None,
        'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_error_message(exc):
    """
    Extrae un mensaje de error legible de la excepción.
    """
    if hasattr(exc, 'detail'):
        detail = exc.detail
        
        # Si es un diccionario, obtener el primer error
        if isinstance(detail, dict):
            first_key = next(iter(detail))
            first_error = detail[first_key]
            
            # Si el error es una lista, tomar el primero
            if isinstance(first_error, list):
                return f"{first_key}: {first_error[0]}"
            return f"{first_key}: {first_error}"
        
        # Si es una lista
        if isinstance(detail, list):
            return str(detail[0])
        
        # String simple
        return str(detail)
    
    # Fallback al nombre de la clase
    return exc.__class__.__name__.replace('_', ' ').title()


class SpotifyAPIException(Exception):
    """Excepción personalizada para errores de la API de Spotify"""
    
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class TokenExpiredException(Exception):
    """Excepción cuando el token de Spotify ha expirado"""
    pass


class SpotifyNotLinkedException(Exception):
    """Excepción cuando el usuario no tiene cuenta de Spotify vinculada"""
    pass
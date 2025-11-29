from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    Maneja excepciones de forma consistente en toda la API
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response = {
            'error': True,
            'message': str(exc),
            'details': response.data
        }
        response.data = custom_response
    
    return response
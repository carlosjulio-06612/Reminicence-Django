from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 

# Create your views here.

@login_required
def home_view(request):
    """
    Vista para la página de inicio/dashboard.
    Solo accesible para usuarios autenticados.
    """
    # Aquí puedes agregar lógica en el futuro para pasar datos a la plantilla
    context = {
        'user': request.user,
    }
    return render(request, 'core/index.html', context)
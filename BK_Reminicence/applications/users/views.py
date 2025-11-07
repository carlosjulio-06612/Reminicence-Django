from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from applications.spotify_api.utils import save_spotify_tokens

def login_view(request):
    # Si la petición es POST, el usuario está enviando el formulario
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Usamos la función de Django para validar al usuario
        user = authenticate(request, username=username, password=password)

        # Si 'user' no es None, las credenciales son correctas
        if user is not None:
            # Usamos la función de Django para iniciar la sesión
            login(request, user)
            # Redirigimos al usuario a la página principal
            return redirect('/') # O a '/dashboard/' o donde prefieras
        else:
            # Si las credenciales son incorrectas, volvemos a mostrar el formulario
            # con un mensaje de error.
            error_message = "Nombre de usuario o contraseña incorrectos."
            return render(request, 'users/login.html', {'error_message': error_message})

    # Si la petición es GET, simplemente mostramos el formulario vacío
    return render(request, 'users/login.html')

def link_spotify_view(request):
    """
    Página de vinculación segura cuando un usuario intenta hacer login con Spotify
    pero su email ya existe con contraseña tradicional.

    Solicita la contraseña para confirmar identidad antes de vincular.
    """
    # Verificar que hay tokens pendientes en sesión
    pending_tokens = request.session.get('pending_spotify_tokens')
    conflict_email = request.session.get('spotify_email_conflict')
    
    if not pending_tokens or not conflict_email:
        # No hay nada pendiente, redirigir al login
        return redirect('/accounts/login/')
    
    if request.method == 'POST':
        password = request.POST.get('password')
        
        # Autenticar al usuario con su contraseña
        user = authenticate(request, username=conflict_email, password=password)
        
        # Si la contraseña no funciona, intentar con username en caso que sea diferente al email
        if not user:
            from django.contrib.auth.models import User
            user_obj = User.objects.filter(email=conflict_email).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
        
        if user is not None:
            # Contraseña correcta - Vincular Spotify
            tokens = pending_tokens
            save_spotify_tokens(
                user,
                tokens['access_token'],
                tokens['refresh_token'],
                tokens['expires_in'],
                tokens['scope'],
                tokens['spotify_user_id']
            )
            
            # Loguear al usuario
            login(request, user)
            
            # Limpiar sesión
            del request.session['pending_spotify_tokens']
            del request.session['spotify_email_conflict']
            
            # Redirigir al dashboard
            return redirect('/')
        else:
            # Contraseña incorrecta
            error_message = "Contraseña incorrecta. Por favor, intenta nuevamente."
            return render(request, 'users/link_spotify.html', {
                'error_message': error_message,
                'email': conflict_email
            })
    
    # GET request - Mostrar formulario
    return render(request, 'users/link_spotify.html', {'email': conflict_email})
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

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
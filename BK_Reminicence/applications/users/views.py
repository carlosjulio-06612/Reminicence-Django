from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from applications.spotify_api.models import SpotifyUserToken
from applications.users.forms import UserProfileUpdateForm, UserRegisterForm
from django.contrib.auth.decorators import login_required


def login_view(request):
    """Vista de login tradicional con usuario y contraseña"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('core:index')
        else:
            messages.error(request, "Nombre de usuario o contraseña incorrectos.")

    return render(request, 'users/login.html')


def logout_view(request):
    """Cerrar sesión del usuario"""
    # Limpiar mensajes antes de hacer logout para evitar que persistan
    storage = messages.get_messages(request)
    storage.used = True
    
    logout(request)
    return redirect('users:login')


def link_spotify_view(request):
    """
    Página intermedia cuando un usuario intenta login con Spotify
    pero su email ya existe con contraseña tradicional.
    Requiere confirmar contraseña antes de vincular.
    """
    pending_tokens = request.session.get('pending_spotify_tokens')
    conflict_email = request.session.get('spotify_email_conflict')
    
    if not pending_tokens or not conflict_email:
        return redirect('users:login')
    
    if request.method == 'POST':
        password = request.POST.get('password')
        
        # Intentar autenticar con email como username
        user = authenticate(request, username=conflict_email, password=password)
        
        # Si falla, intentar con el username real
        if not user:
            from django.contrib.auth.models import User
            from applications.spotify_api.utils import save_spotify_tokens
            
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
            
            # Loguear y limpiar sesión
            login(request, user)
            del request.session['pending_spotify_tokens']
            del request.session['spotify_email_conflict']
            
            messages.success(request, 'Tu cuenta de Spotify ha sido vinculada exitosamente.', extra_tags='settings_page')
            return redirect('core:index')
        else:
            messages.error(request, "Contraseña incorrecta.")
            return render(request, 'users/link_spotify.html', {'email': conflict_email})
    
    return render(request, 'users/link_spotify.html', {'email': conflict_email})


class register_view(CreateView):
    """Vista de registro de nuevos usuarios"""
    form_class = UserRegisterForm
    success_url = reverse_lazy('users:login')
    template_name = 'users/register.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(self.request, f'¡Cuenta creada para {username}! Ahora puedes iniciar sesión.', extra_tags='login_page')
        return response


@login_required
def settings_view(request):
    """Vista principal de configuración de cuenta"""
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Tu perfil ha sido actualizado con éxito!', extra_tags='settings_page')
            return redirect('users:settings')
    else:
        form = UserProfileUpdateForm(instance=request.user)

    # Verificar si Spotify está vinculado
    spotify_linked = SpotifyUserToken.objects.filter(user=request.user).exists()

    context = {
        'form': form,
        'spotify_linked': spotify_linked
    }
    return render(request, 'users/settings.html', context)


@login_required
def unlink_spotify_view(request):
    """Desvincular cuenta de Spotify"""
    if request.method == 'POST':
        try:
            token = SpotifyUserToken.objects.get(user=request.user)
            token.delete()
            messages.success(request, 'Tu cuenta de Spotify ha sido desvinculada correctamente.', extra_tags='settings_page')
        except SpotifyUserToken.DoesNotExist:
            messages.warning(request, 'Tu cuenta no estaba vinculada a Spotify.', extra_tags='settings_page')
        except Exception as e:
            messages.error(request, 'Ocurrió un error al desvincular tu cuenta.', extra_tags='settings_page')
    
    return redirect('users:settings')


@login_required
def confirm_delete_account(request):
    """Muestra la página de confirmación para eliminar cuenta"""
    return render(request, 'users/confirm_delete_account.html')


@login_required
def delete_account_view(request):
    """Elimina permanentemente la cuenta del usuario"""
    if request.method == 'POST':
        password = request.POST.get('password')

        if request.user.check_password(password):
            username = request.user.username
            request.user.delete()
            
            # Limpiar mensajes antes de logout
            storage = messages.get_messages(request)
            storage.used = True
            
            logout(request)
            # No agregar mensaje aquí porque se mostrará en login
            return redirect('core:index')
        else:
            messages.error(request, 'Contraseña incorrecta.')
            return render(request, 'users/confirm_delete_account.html', {'error': 'Contraseña incorrecta.'})
            
    return redirect('users:confirm_delete_account')


@login_required
def change_password_view(request):
    """Permite cambiar la contraseña del usuario autenticado"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Mantener la sesión activa después del cambio
            update_session_auth_hash(request, user)
            messages.success(request, '¡Tu contraseña ha sido cambiada exitosamente!', extra_tags='settings_page')
            return redirect('users:settings')
        else:
            messages.error(request, 'Por favor corrige los errores.', extra_tags='settings_page')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users/password/change_password.html', {'form': form})
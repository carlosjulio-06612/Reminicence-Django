# applications/users/urls.py

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # --- Tus URLs de Login, Logout y Registro ---
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    path('register/', views.register_view.as_view(), name='register'),

    # --- Password Reset URLs ---
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='users/password/password_reset_form.html',
             email_template_name='users/password/password_reset_email.html',
             success_url=reverse_lazy('users:password_reset_done')
         ), 
         name='password_reset'),

    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password/password_reset_done.html'
         ), 
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password/password_reset_confirm.html',
             success_url=reverse_lazy('users:password_reset_complete')
         ), 
         name='password_reset_confirm'),

    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # --- Settings URLs ---
    path('settings/', views.settings_view, name='settings'),
    path('settings/unlink-spotify/', views.unlink_spotify_view, name='unlink_spotify'),
    path('settings/confirm-delete/', views.confirm_delete_account, name='confirm_delete_account'),  # NUEVA
    path('settings/delete-account/', views.delete_account_view, name='delete_account'),
    
    # --- Change Password (authenticated users) ---
    path('change-password/', views.change_password_view, name='change_password'),  # NUEVA
]
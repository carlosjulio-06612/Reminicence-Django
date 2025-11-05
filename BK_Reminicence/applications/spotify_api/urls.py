from django.urls import path
from . import views

app_name = 'spotify_api'

urlpatterns = [
    path('login/', views.spotify_login_view, name='spotify_login'),
    path('callback/', views.spotify_callback_view, name='spotify_callback'),
]
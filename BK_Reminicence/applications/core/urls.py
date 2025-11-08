from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('spotify/disconnect/', views.disconnect_spotify, name='disconnect_spotify'),
    path('spotify/sync/', views.sync_spotify_data, name='sync_spotify'),
]
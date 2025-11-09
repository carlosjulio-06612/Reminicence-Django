from django.urls import path
from . import views

app_name = 'music'

urlpatterns = [
    path('playlist/<str:playlist_id>/', views.playlist_detail_view, name='playlist_detail'),
    path('artist/<str:artist_id>/', views.artist_detail_view, name='artist_detail'),
    path('album/<str:album_id>/', views.album_detail_view, name='album_detail'),
    path('search/', views.search_view, name='search'),
]
from django.urls import path
from . import views

app_name = 'music'

urlpatterns = [
    path('playlist/<str:playlist_id>/', views.playlist_detail_view, name='playlist_detail'),
]
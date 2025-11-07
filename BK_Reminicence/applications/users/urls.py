from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('link-spotify/', views.link_spotify_view, name='link_spotify'),
]
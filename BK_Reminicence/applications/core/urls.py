from django.urls import path
from .views import map_points

urlpatterns = [
    path("map/points/", map_points, name="map_points"),
]
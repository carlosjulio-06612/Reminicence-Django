from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet, 
    CustomTokenObtainPairView,
    PasswordResetRequestView,  
    PasswordResetConfirmView    
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    # Auth endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Password Reset endpoints (NUEVOS)
    path('users/password_reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('users/password_reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    
    path('', include(router.urls)),
]
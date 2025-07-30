from rest_framework_simplejwt.views import TokenRefreshView
from django.urls import path
from .views import (
    CustomTokenObtainPairView,
    CreateUserView,
    RetrieveUpdateDeleteUser,
)


urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", CreateUserView.as_view(), name="create_user"),
    path("profile/", RetrieveUpdateDeleteUser.as_view(), name="profile_user"),
]

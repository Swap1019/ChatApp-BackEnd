from django.urls import path
from .views import (
    HomeView,
    ConversationDataRetrieveView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<uuid:uuid>/", ConversationDataRetrieveView.as_view(), name="home"),
]
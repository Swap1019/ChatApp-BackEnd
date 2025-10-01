from django.urls import path
from .views import (
    HomeView,
    ConversationDataRetrieveView,
    ConversationMembersDataRetrieveView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<uuid:uuid>/", ConversationDataRetrieveView.as_view(), name="conversation"),
    path("<uuid:uuid>/members", ConversationMembersDataRetrieveView.as_view(), name="conversation-members"),
]
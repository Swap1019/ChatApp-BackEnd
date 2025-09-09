from django.urls import path
from .views import (
    HomeView,
    ConversationDataRetrieveView,
    CreateMessageView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<uuid:uuid>/", ConversationDataRetrieveView.as_view(), name="home"),
    path("message/create/", CreateMessageView.as_view(), name="message-create"),
]
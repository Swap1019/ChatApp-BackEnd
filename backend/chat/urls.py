from django.urls import path
from .views import (
    HomeView,
    ConversationDataRetrieveView,
    ConversationMembersDataRetrieveView,
    GetOrCreatePrivateConversationView,
    SearchUserDataRetrieveView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<uuid:uuid>/", ConversationDataRetrieveView.as_view(), name="conversation"),
    path(
        "<uuid:uuid>/members/",
        ConversationMembersDataRetrieveView.as_view(),
        name="conversation-members",
    ),
    path(
        "conversations/private/",
        GetOrCreatePrivateConversationView.as_view(),
        name="get-or-create-private-conversation",
    ),
    path("search/users/", SearchUserDataRetrieveView.as_view(), name="search-users"),
]

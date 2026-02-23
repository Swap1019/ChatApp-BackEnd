from django.urls import path
from .views import (
    HomeView,
    ConversationDataRetrieveView,
    ConversationMembersDataRetrieveView,
    SearchUserDataRetrieveView,
    ContactsView,
    ContactDetailView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<uuid:uuid>/", ConversationDataRetrieveView.as_view(), name="conversation"),
    path(
        "<uuid:uuid>/members/",
        ConversationMembersDataRetrieveView.as_view(),
        name="conversation-members",
    ),
    path("search/users/", SearchUserDataRetrieveView.as_view(), name="search-users"),
    path("contacts/", ContactsView.as_view(), name="contacts"),
    path("contacts/<uuid:user_id>/", ContactDetailView.as_view(), name="contact-detail"),
]

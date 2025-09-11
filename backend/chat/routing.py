from django.urls import re_path

from .consumers import ChatRoomConsumer

websocket_urlpatterns = [
    re_path(r'chat/(?P<room_name>[0-9a-f-]{36})/$', ChatRoomConsumer.as_asgi()),
]
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message
from backend.settings import MEDIA_FULL_URL


class ChatRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        # Join group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            return

        data = json.loads(text_data)
        text = data.get("text")

        if not text:
            return

        # Save to DB
        message = await self.create_message(user, text)

        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "id": str(message.id),
                    "content": message.content,
                    "sender": {
                        "id": str(message.sender.id),
                        "nickname": message.sender.nickname,
                        "profile": MEDIA_FULL_URL + message.sender.profile.url,
                    },
                    "created_at": message.created_at.isoformat(),
                    "is_read": message.is_read,
                },
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"]
        }))

    @database_sync_to_async
    def create_message(self, user, text):
        conversation = Conversation.objects.get(id=self.room_name)
        return Message.objects.create(
            conversation=conversation,
            sender=user,
            content=text
        )

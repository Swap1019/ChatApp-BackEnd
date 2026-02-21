import json
from datetime import timedelta

from channels.db import database_sync_to_async
from django.utils import timezone
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer

from user.models import User
from .models import Conversation, Message
from .payloads import build_conversation_payload


class ChatRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

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
        reply_to = data.get("reply_to")

        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        if not text:
            return

        result = await self.create_message(user, text, reply_to)
        if not result["created"]:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": result["message"],
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"message": event["message"]}))

    @database_sync_to_async
    def create_message(self, user, text, reply_to_id=None):
        conversation = Conversation.objects.get(id=self.room_name)
        reply_to_message = None
        if reply_to_id:
            reply_to_message = (
                Message.objects.filter(id=reply_to_id, conversation=conversation).first()
            )

        # Guard against rapid duplicate submits from mobile browsers.
        recent = (
            Message.objects.filter(
                conversation=conversation,
                sender=user,
                content=text,
                created_at__gte=timezone.now() - timedelta(milliseconds=700),
            )
            .order_by("-created_at")
            .first()
        )
        if recent:
            message = recent
            created = False
        else:
            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=text,
                reply_to=reply_to_message,
            )
            created = True

        return {
            "created": created,
            "message": {
                "id": str(message.id),
                "content": message.content,
                "sender": {
                    "id": str(user.id),
                    "nickname": user.nickname,
                    "profile_url": user.profile_url,
                },
                "created_at": message.created_at.isoformat(),
                "is_read": message.is_read,
                "reply_to": (
                    str(message.reply_to_id) if message.reply_to_id is not None else None
                ),
            },
        }


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
            return

        if msg_type == "create_private_conversation":
            other_user_id = content.get("user_id")
            if not other_user_id:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "missing_user_id",
                        "detail": "user_id is required",
                    }
                )
                return

            result = await self.get_or_create_private_conversation(other_user_id)
            if result.get("error"):
                await self.send_json(
                    {
                        "type": "error",
                        "code": result["error"],
                        "detail": result["detail"],
                    }
                )
                return

            await self.channel_layer.group_send(
                f"user_{self.user.id}",
                {
                    "type": "new_conversation",
                    "conversation": result["creator_payload"],
                },
            )

            if result["created"]:
                await self.channel_layer.group_send(
                    f"user_{result['other_user_id']}",
                    {
                        "type": "new_conversation",
                        "conversation": result["recipient_payload"],
                    },
                )

            await self.send_json(
                {
                    "type": "private_conversation_ready",
                    "conversation": result["creator_payload"],
                    "created": result["created"],
                }
            )

    async def new_conversation(self, event):
        await self.send_json(
            {"type": "new_conversation", "conversation": event["conversation"]}
        )

    @database_sync_to_async
    def get_or_create_private_conversation(self, other_user_id):
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return {"error": "user_not_found", "detail": "User was not found"}

        if other_user.id == self.user.id:
            return {
                "error": "invalid_target",
                "detail": "Cannot create a private conversation with yourself",
            }

        conversation = (
            Conversation.objects.filter(is_group=False)
            .filter(members=self.user)
            .filter(members=other_user)
            .distinct()
            .first()
        )

        created = False
        if not conversation:
            conversation = Conversation.objects.create(is_group=False)
            conversation.members.add(self.user, other_user)
            created = True

        creator_payload = build_conversation_payload(conversation, self.user)
        recipient_payload = build_conversation_payload(conversation, other_user)
        return {
            "created": created,
            "creator_payload": creator_payload,
            "recipient_payload": recipient_payload,
            "other_user_id": str(other_user.id),
        }

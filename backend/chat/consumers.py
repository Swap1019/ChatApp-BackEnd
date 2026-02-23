import json
import base64
import os
import uuid
from io import BytesIO
from datetime import timedelta
from collections import Counter

from channels.db import database_sync_to_async
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count
from django.conf import settings
from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
    AsyncWebsocketConsumer,
)
from PIL import Image, UnidentifiedImageError

from user.models import User
from .models import Conversation, Message, MessagesMedia
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
        attachments = data.get("attachments") or []

        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        if not text and not attachments:
            return

        result = await self.create_message(user, text or "", reply_to, attachments)
        if not result["created"]:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": result["message"],
            },
        )
        await self.notify_conversation_updates(
            result["conversation_id"],
            result["member_ids"],
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"message": event["message"]}))

    @database_sync_to_async
    def create_message(self, user, text, reply_to_id=None, attachments=None):
        conversation = Conversation.objects.get(id=self.room_name)
        member_ids = [
            str(member_id)
            for member_id in conversation.members.values_list("id", flat=True)
        ]
        reply_to_message = None
        attachments = attachments or []
        if reply_to_id:
            reply_to_message = Message.objects.filter(
                id=reply_to_id, conversation=conversation
            ).first()

        # Guard against rapid duplicate submits from mobile browsers.
        recent = None
        if text and not attachments:
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
        created_media_files = []
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
            for attachment in attachments:
                url = attachment.get("url")
                kind = attachment.get("kind")
                name = attachment.get("name")
                if not url:
                    continue
                media = MessagesMedia.objects.create(
                    message=message, file=url, kind=kind, name=name,
                )
                created_media_files.append(
                    {
                        "name": name,
                        "id": str(media.id),
                        "file": url,
                        "kind": kind,
                    }
                )
            created = True

        media_files = (
            created_media_files
            if created_media_files
            else [
                {"id": str(media.id), "file": str(media.file), "kind": media.kind}
                for media in message.media_files.all()
            ]
        )

        return {
            "created": created,
            "conversation_id": str(conversation.id),
            "member_ids": member_ids,
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
                "media_files": media_files,
                "reply_to": (
                    str(message.reply_to_id)
                    if message.reply_to_id is not None
                    else None
                ),
            },
        }

    async def notify_conversation_updates(self, conversation_id, member_ids):
        payloads = await self.get_conversation_updates_for_members(
            conversation_id, member_ids
        )
        for member_id, update_payload in payloads.items():
            await self.channel_layer.group_send(
                f"user_{member_id}",
                {
                    "type": "conversation_update",
                    "conversation": update_payload,
                },
            )

    @database_sync_to_async
    def get_conversation_updates_for_members(self, conversation_id, member_ids):
        try:
            conversation = (
                Conversation.objects.filter(id=conversation_id)
                .prefetch_related("members", "admins")
                .first()
            )
            if not conversation:
                return {}

            members = list(conversation.members.all())
            members_by_id = {str(member.id): member for member in members}
            target_member_ids = [member_id for member_id in member_ids if member_id in members_by_id]
            if not target_member_ids:
                return {}

            last_message = (
                Message.objects.filter(conversation=conversation)
                .select_related("sender")
                .order_by("-created_at")
                .first()
            )
            unread_grouped = list(
                Message.objects.filter(conversation=conversation, is_read=False)
                .values("sender_id")
                .annotate(total=Count("id"))
            )
            unread_by_sender = Counter(
                {row["sender_id"]: row["total"] for row in unread_grouped}
            )
            total_unread = sum(unread_by_sender.values())

            sender_name = None
            last_message_preview = None
            if last_message:
                sender_name = (
                    last_message.sender.nickname
                    if last_message.sender and last_message.sender.nickname
                    else (
                        last_message.sender.username if last_message.sender else "Unknown"
                    )
                )
                last_message_preview = {
                    "id": str(last_message.id),
                    "content": last_message.content or "",
                    "sender_nickname": sender_name,
                    "created_at": last_message.created_at.isoformat(),
                }

            admin_ids = set(
                str(admin_id)
                for admin_id in conversation.admins.values_list("id", flat=True)
            )
            creator_id = str(conversation.created_by_id) if conversation.created_by_id else None

            # Cache the "other user" once for private conversations.
            private_other_by_viewer = {}
            if not conversation.is_group and len(members) == 2:
                a, b = members[0], members[1]
                private_other_by_viewer[str(a.id)] = b
                private_other_by_viewer[str(b.id)] = a

            payloads = {}
            for member_id in target_member_ids:
                viewer = members_by_id[member_id]
                viewer_uuid = str(viewer.id)
                unread_count = total_unread - unread_by_sender.get(viewer.id, 0)
                base_payload = {
                    "id": str(conversation.id),
                    "is_group": conversation.is_group,
                    "created_by": creator_id,
                    "viewer_is_creator": creator_id == viewer_uuid,
                    "viewer_is_admin": viewer_uuid in admin_ids,
                    "unread_count": unread_count,
                    "last_message": last_message_preview,
                }

                if conversation.is_group:
                    base_payload["name"] = conversation.name
                    base_payload["profile_url"] = conversation.profile_url
                else:
                    other_user = private_other_by_viewer.get(viewer_uuid)
                    if not other_user:
                        # Fallback to original behavior if membership shape is unexpected.
                        payloads[member_id] = build_conversation_payload(conversation, viewer)
                        continue
                    base_payload["name"] = other_user.nickname or other_user.username
                    base_payload["profile_url"] = other_user.profile_url

                payloads[member_id] = base_payload

            return payloads
        except Exception:
            return {}


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
        if msg_type == "mark_conversation_read":
            conversation_id = content.get("conversation_id")
            if not conversation_id:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "missing_conversation_id",
                        "detail": "conversation_id is required",
                    }
                )
                return

            update_payload = await self.mark_conversation_read(conversation_id)
            if not update_payload:
                await self.send_json(
                    {
                        "type": "error",
                        "code": "conversation_not_found",
                        "detail": "Conversation was not found for this user",
                    }
                )
                return

            await self.channel_layer.group_send(
                f"user_{self.user.id}",
                {
                    "type": "conversation_update",
                    "conversation": update_payload,
                },
            )
            return

        if msg_type == "create_group_conversation":
            name = content.get("name")
            member_ids = content.get("member_ids") or []
            profile_data_url = content.get("profile_data_url")
            profile_name = content.get("profile_name")
            result = await self.create_group_conversation(
                name, member_ids, profile_data_url, profile_name
            )
            if result.get("error"):
                await self.send_json(
                    {
                        "type": "error",
                        "code": result["error"],
                        "detail": result["detail"],
                    }
                )
                return

            for member_id, payload in result["member_payloads"].items():
                await self.channel_layer.group_send(
                    f"user_{member_id}",
                    {
                        "type": "new_conversation",
                        "conversation": payload,
                    },
                )

            await self.send_json(
                {
                    "type": "group_conversation_ready",
                    "conversation": result["creator_payload"],
                }
            )
            return

        if msg_type == "add_group_members":
            conversation_id = content.get("conversation_id")
            member_ids = content.get("member_ids") or []
            result = await self.add_group_members(conversation_id, member_ids)
            if result.get("error"):
                await self.send_json(
                    {
                        "type": "error",
                        "code": result["error"],
                        "detail": result["detail"],
                    }
                )
                return

            for member_id, payload in result["new_member_payloads"].items():
                await self.channel_layer.group_send(
                    f"user_{member_id}",
                    {
                        "type": "new_conversation",
                        "conversation": payload,
                    },
                )

            await self.send_json(
                {
                    "type": "group_members_added",
                    "conversation": result["requester_payload"],
                    "added_count": result["added_count"],
                    "detail": "Members added successfully.",
                }
            )
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

    async def conversation_update(self, event):
        await self.send_json(
            {"type": "conversation_update", "conversation": event["conversation"]}
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

    @database_sync_to_async
    def create_group_conversation(
        self, name, member_ids, profile_data_url=None, profile_name=None
    ):
        cleaned_name = (name or "").strip() or "New Group"
        normalized_ids = {str(member_id) for member_id in (member_ids or [])}
        normalized_ids.add(str(self.user.id))

        users = list(User.objects.filter(id__in=normalized_ids))
        user_map = {str(user.id): user for user in users}
        user_map[str(self.user.id)] = self.user

        conversation = Conversation.objects.create(
            is_group=True,
            name=cleaned_name,
            created_by=self.user,
        )
        if profile_data_url and isinstance(profile_data_url, str):
            profile_url = self._save_data_url_as_webp(
                profile_data_url, profile_name, folder="group_profiles"
            )
            if profile_url:
                conversation.profile = self._to_absolute_media_url(profile_url)
                conversation.save(update_fields=["profile"])
        conversation.members.add(*user_map.values())
        conversation.admins.add(self.user)

        member_payloads = {}
        for member in user_map.values():
            member_payloads[str(member.id)] = build_conversation_payload(
                conversation, member
            )

        return {
            "creator_payload": member_payloads[str(self.user.id)],
            "member_payloads": member_payloads,
        }

    @staticmethod
    def _save_data_url_as_webp(data_url, file_name, folder):
        try:
            header, encoded = data_url.split(",", 1)
            if ";base64" not in header:
                return None

            raw_bytes = base64.b64decode(encoded)
            image = Image.open(BytesIO(raw_bytes))
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=82, method=6)
            output.seek(0)

            base_name = os.path.splitext(file_name or "group")[0] or "group"
            filename = f"{base_name}_{uuid.uuid4().hex}.webp"
            storage_path = os.path.join(folder, filename)
            saved_path = default_storage.save(
                storage_path, ContentFile(output.read())
            )
            return default_storage.url(saved_path)
        except (ValueError, UnidentifiedImageError, OSError):
            return None

    def _to_absolute_media_url(self, media_url):
        if not media_url:
            return media_url
        if media_url.startswith("http://") or media_url.startswith("https://"):
            return media_url

        if settings.MEDIA_PUBLIC_BASE_URL:
            if media_url.startswith("/"):
                return f"{settings.MEDIA_PUBLIC_BASE_URL}{media_url}"
            return f"{settings.MEDIA_PUBLIC_BASE_URL}/{media_url}"

        headers = dict(self.scope.get("headers", []))
        host = headers.get(b"host", b"").decode("utf-8")
        if not host:
            return media_url

        scheme = "https" if self.scope.get("scheme") == "wss" else "http"
        if media_url.startswith("/"):
            return f"{scheme}://{host}{media_url}"
        return f"{scheme}://{host}/{media_url}"

    @database_sync_to_async
    def add_group_members(self, conversation_id, member_ids):
        if not conversation_id:
            return {
                "error": "missing_conversation_id",
                "detail": "conversation_id is required",
            }

        try:
            conversation = Conversation.objects.get(id=conversation_id, is_group=True)
        except Conversation.DoesNotExist:
            return {
                "error": "conversation_not_found",
                "detail": "Group conversation was not found",
            }

        if not conversation.members.filter(id=self.user.id).exists():
            return {
                "error": "not_group_member",
                "detail": "You are not a member of this group",
            }

        is_creator = conversation.created_by_id == self.user.id
        is_admin = conversation.admins.filter(id=self.user.id).exists()
        if not (is_creator or is_admin):
            return {
                "error": "forbidden",
                "detail": "Only group creator/admin can add members",
            }

        normalized_ids = {str(member_id) for member_id in (member_ids or [])}
        if not normalized_ids:
            return {
                "error": "missing_member_ids",
                "detail": "member_ids is required",
            }

        users_to_add = list(User.objects.filter(id__in=normalized_ids))
        existing_ids = set(
            str(member_id)
            for member_id in conversation.members.values_list("id", flat=True)
        )
        new_users = [
            member for member in users_to_add if str(member.id) not in existing_ids
        ]

        if new_users:
            conversation.members.add(*new_users)

        new_member_payloads = {}
        for member in new_users:
            new_member_payloads[str(member.id)] = build_conversation_payload(
                conversation, member
            )

        return {
            "added_count": len(new_users),
            "new_member_payloads": new_member_payloads,
            "requester_payload": build_conversation_payload(conversation, self.user),
        }

    @database_sync_to_async
    def mark_conversation_read(self, conversation_id):
        try:
            conversation = Conversation.objects.get(
                id=conversation_id, members=self.user
            )
        except Conversation.DoesNotExist:
            return None

        Message.objects.filter(
            conversation=conversation,
            is_read=False,
        ).exclude(
            sender=self.user
        ).update(is_read=True)
        return build_conversation_payload(conversation, self.user)

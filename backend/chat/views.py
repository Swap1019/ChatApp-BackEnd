import json

from redis import Redis
from redis.exceptions import RedisError
from rest_framework.views import APIView
from rest_framework.generics import (
    RetrieveAPIView,
)
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import (
    IsAuthenticated,
)
from user.serializers import (
    UserSettingsSerializer,
    UserSerializer,
)

from .serializer import (
    ConversationSerializer,
    MessageSerializer,
    MemberSearchSerializer,
    ContactSerializer,
    AddContactSerializer,
)

from .models import (
    Message,
    Conversation,
    Contact,
)
from user.models import User
from .documents import (
    UserDocument,
)
from .payloads import build_conversation_payload

MESSAGE_PAGE_SIZE = 50
MESSAGE_CACHE_TTL_SECONDS = 30
_redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


class HomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        user_data = UserSettingsSerializer(
            request.user, context={"request": request}
        ).data

        conversations = request.user.chats.defer("created_at", "members").all()
        con_data = [
            build_conversation_payload(conv, request.user) for conv in conversations
        ]

        return Response({"user": user_data, "conversations": con_data})


class ConversationDataRetrieveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        page_raw = request.query_params.get("page", "1")
        try:
            page = int(page_raw)
        except (TypeError, ValueError):
            page = 1
        if page < 1:
            page = 1

        conversation = get_object_or_404(
            Conversation.objects.defer("created_at", "members"),
            id=uuid,
            members=request.user,
        )
        cache_key = f"chat:{uuid}:messages:page:{page}:size:{MESSAGE_PAGE_SIZE}"
        try:
            cached_page = _redis_client.get(cache_key)
        except RedisError:
            cached_page = None

        if cached_page:
            page_payload = json.loads(cached_page)
            msg_data = page_payload["messages"]
            has_more = page_payload["has_more"]
            next_page = page_payload["next_page"]
        else:
            start = (page - 1) * MESSAGE_PAGE_SIZE
            stop = start + MESSAGE_PAGE_SIZE + 1
            queryset = (
                Message.objects.filter(conversation_id=uuid)
                .select_related("sender", "reply_to")
                .prefetch_related("media_files")
                .only(
                    "id",
                    "sender__id",
                    "sender__nickname",
                    "sender__profile",
                    "conversation",
                    "content",
                    "reply_to",
                    "created_at",
                    "is_read",
                )
                .order_by("-created_at")[start:stop]
            )
            rows = list(queryset)
            has_more = len(rows) > MESSAGE_PAGE_SIZE
            rows = rows[:MESSAGE_PAGE_SIZE]
            rows.reverse()
            msg_data = MessageSerializer(
                rows,
                context={"request": request},
                many=True,
            ).data
            next_page = page + 1 if has_more else None
            try:
                _redis_client.setex(
                    cache_key,
                    MESSAGE_CACHE_TTL_SECONDS,
                    json.dumps(
                        {
                            "messages": msg_data,
                            "has_more": has_more,
                            "next_page": next_page,
                        },
                        default=str,
                    ),
                )
            except RedisError:
                pass

        con_data = ConversationSerializer(
            conversation,
            context={"request": request},
        ).data

        return Response(
            {
                "conversation": con_data,
                "messages": msg_data,
                "pagination": {
                    "page": page,
                    "page_size": MESSAGE_PAGE_SIZE,
                    "has_more": has_more,
                    "next_page": next_page,
                },
            }
        )


class ConversationMembersDataRetrieveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        conversation = get_object_or_404(Conversation.objects.only("id"), id=uuid)
        if not conversation.is_group:
            other_user = conversation.get_other_member(request.user)
            serializer = UserSerializer(other_user, context={"request": request})
            return Response({"other_user": serializer.data})

        else:
            members = conversation.members.only(
                "id", "username", "nickname", "bio", "profile"
            )
            serializer = UserSerializer(
                members, many=True, context={"request": request}
            )

            return Response({"members": serializer.data})


class SearchUserDataRetrieveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query = (request.GET.get("q") or "").strip()
        if not query:
            return Response([])

        search = UserDocument.search().query(
            "multi_match",
            query=query,
            fields=["username", "nickname", "phone_number"],
            type="phrase_prefix",
        )[:20]

        results = [
            {
                "id": hit.id,
                "username": hit.username,
                "nickname": hit.nickname,
                "phone_number": getattr(hit, "phone_number", None),
                "profile_url": hit.profile_url,
            }
            for hit in search
        ]

        serializer = MemberSearchSerializer(results, many=True)
        return Response(serializer.data)


class ContactsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        contacts = (
            Contact.objects.filter(owner=request.user)
            .select_related("contact")
            .order_by("-created_at")
        )
        serializer = ContactSerializer(contacts, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = AddContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data["user_id"]

        if str(user_id) == str(request.user.id):
            return Response(
                {"detail": "You cannot add yourself to contacts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact_user = get_object_or_404(User, id=user_id)
        contact, created = Contact.objects.get_or_create(
            owner=request.user, contact=contact_user
        )
        response_serializer = ContactSerializer(contact, context={"request": request})
        return Response(
            {
                "detail": "Contact added." if created else "Contact already exists.",
                "contact": response_serializer.data,
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ContactDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id=None, *args, **kwargs):
        contact = Contact.objects.filter(owner=request.user, contact_id=user_id).first()
        if not contact:
            return Response(
                {"detail": "Contact not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

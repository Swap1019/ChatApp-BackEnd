from rest_framework.views import APIView
from rest_framework.generics import (
    RetrieveAPIView,
)
from django.shortcuts import get_object_or_404
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
        msg_data = MessageSerializer(
            Message.objects.filter(conversation_id=uuid)
            .select_related("sender", "reply_to")
            .prefetch_related("media_files")
            .only(
                "sender__id",
                "sender__nickname",
                "sender__profile",
                "conversation",
                "content",
                "reply_to",
                "created_at",
                "is_read",
            ),
            context={"request": request},
            many=True,
        ).data

        con_data = ConversationSerializer(
            Conversation.objects.defer("created_at", "members").get(id=uuid),
            context={"request": request},
        ).data

        return Response({"conversation": con_data, "messages": msg_data})


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
        search = UserDocument.search().query(
            "multi_match",
            query=request.GET.get("q"),
            fields=["username", "nickname"],
            type="phrase_prefix",
        )[:20]

        results = [
            {
                "id": hit.id,
                "username": hit.username,
                "nickname": hit.nickname,
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

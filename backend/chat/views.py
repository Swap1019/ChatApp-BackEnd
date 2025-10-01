from rest_framework.views import (
    APIView,
)
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
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
)

from .models import (
    Message,
    Conversation,
)


class HomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        user_data = UserSettingsSerializer(
            request.user, context={"request": request}
        ).data
        con_data = ConversationSerializer(
            request.user.chats.defer("created_at", "members").all(),
            many=True,
            context={"request": request},
        ).data

        return Response({"user": user_data, "conversations": con_data})


class ConversationDataRetrieveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        msg_data = MessageSerializer(
            Message.objects.filter(conversation_id=uuid)
            .select_related("sender")
            .only(
                "sender__id",
                "sender__nickname",
                "sender__profile",
                "conversation",
                "content",
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

        members = conversation.members.only("id","username","nickname","bio","profile")
        serializer = UserSerializer(members, many=True, context={"request": request})

        return Response({"members": serializer.data})

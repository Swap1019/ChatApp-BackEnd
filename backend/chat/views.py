from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
)
from user.serializers import (
    UserSerializer,
)
from .serializer import ConversationSerializer, MessageSerializer
from .models import (
    Message,
)


class HomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        user_data = UserSerializer(request.user).data
        conv_data = ConversationSerializer(request.user.chats.all(), many=True).data

        if uuid:  # if /chat/<uuid>
            msg_data = MessageSerializer(
                Message.objects.filter(conversation_id=uuid).select_related("sender"),
                many=True,
            ).data
            return Response(
                {"user": user_data, "conversations": conv_data, "messages": msg_data}
            )
        return Response({"user": user_data, "conversations": conv_data})


class ConversationDataRetrieveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        msg_data = MessageSerializer(
            Message.objects.filter(conversation_id=uuid).select_related("sender"),
            many=True,
        ).data
        return Response({"messages": msg_data})

from rest_framework.views import (
    APIView,
)
from rest_framework.generics import CreateAPIView
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
        user_data = UserSerializer(request.user, context={"request": request}).data
        conv_data = ConversationSerializer(request.user.chats.all(), many=True, context={"request": request}).data

        if uuid:  # if /chat/<uuid>
            msg_data = MessageSerializer(
                Message.objects.filter(conversation_id=uuid).select_related("sender"),
                context={"request": request},
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
            context={"request": request},
            many=True,
        ).data
        return Response({"messages": msg_data})


class CreateMessageView(CreateAPIView):
    queryset = Message.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

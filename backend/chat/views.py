from rest_framework.views import (
    APIView,
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.generics import (
    RetrieveAPIView,
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
    MemberSearchSerializer,
)

from .models import (
    Message,
    Conversation,
)
from user.models import User
from .documents import (
    UserDocument,
)


class HomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid=None, *args, **kwargs):
        user_data = UserSettingsSerializer(
            request.user, context={"request": request}
        ).data

        conversations = request.user.chats.defer("created_at", "members").all()

        data = []
        for conv in conversations:
            if not conv.is_group:
                other_user = conv.get_other_member(request.user)
                data.append(
                    {
                        "id": conv.id,
                        "name": other_user.nickname,
                        "profile_url": other_user.profile_url,
                        "is_group": conv.is_group,
                    }
                )
            else:
                data.append(conv)

        con_data = ConversationSerializer(
            data,
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


class GetOrCreatePrivateConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        other_user_id = request.data.get("user_id")

        if not other_user_id:
            return Response(
                {"detail": "user_id is required"},
                status=400,
            )

        other_user = get_object_or_404(User, id=other_user_id)
        me = request.user

        conversation = Conversation.objects.filter(is_group=False).filter(members=me).filter(members=other_user).distinct().first()
        print(conversation)

        if not conversation:
            conversation = Conversation.objects.create(is_group=False)
            conversation.members.add(me, other_user)
            conversation = ConversationSerializer(
                conversation, context={"request": request}
            ).data
            print(conversation)

        return Response({"conversation": conversation})


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

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSettingsSerializer,
)
from .models import (
    User,
)
from chat.models import Conversation
from user.tasks import upload_user_images
import tempfile


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data

        response = Response(tokens)
        return response


class CreateUserView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSettingsSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
        except ValidationError as e:
            return Response(
                {"detail": "Invalid input", "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {
                    "detail": "User already exists.",
                    "errors": {
                        "username": ["A user with that username already exists."],
                        "email": ["A user with that email already exists."],
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()


class RetrieveUpdateDeleteUser(RetrieveUpdateDestroyAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        user = self.request.user
        data = request.data.copy()

        profile_file = request.FILES.get("profile")
        background_file = request.FILES.get("background_image")

        profile_path, background_path = None, None

        if profile_file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                for chunk in profile_file.chunks():
                    tmp.write(chunk)
                profile_path = tmp.name

        if background_file:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                for chunk in background_file.chunks():
                    tmp.write(chunk)
                background_path = tmp.name

        # Update text fields before image field
        serializer = self.get_serializer(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if profile_path or background_path:
            upload_user_images.delay(str(user.id), profile_path, background_path)
            return Response(
                {"detail": "Profile updated. Images are uploading in background."},
                status=202,
            )

        return Response(
            {"detail": "Your profile has been updated, please reload for the changes"},
            status=200,
        )

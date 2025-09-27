from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
        }
        return data


class UserSettingsSerializer(ModelSerializer):
    profile = serializers.ImageField(use_url=True, required=False)
    background_image = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = [
            "id",
            "date_joined",
            "last_login",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "id": {"read_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(
            password
        )  # these two lines prevent the password to be displayed in the response
        user.save()
        return user

    def update(self, instance, validated_data):
        # Ignoring these fields in case of being sent
        validated_data.pop("password", None)
        validated_data.pop("id", None)

        delete_allowed_fields = ["profile", "nickname", "bio"]

        for attr, value in validated_data.items():
            if attr in delete_allowed_fields or value is not None:
                setattr(
                    instance, attr, value
                )  # this method allows some fields to be empty and restrict the others

        instance.save()
        return instance
    
class UserSerializer(ModelSerializer):
    profile = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = User
        fields = ["id","username","nickname","bio","profile"]


class UserMessageSerializer(ModelSerializer):
    profile = serializers.ImageField(use_url=True, required=False)

    class Meta:
        model = User
        fields = ["id","nickname","profile"]
        



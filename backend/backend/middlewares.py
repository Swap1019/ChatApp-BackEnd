from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user = User.objects.get(id=access_token["user_id"])
        return user
    except Exception:
        return None

class JWTAuthMiddleware:
    """JWT middleware for Channels 3+"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Parse token from query string
        query_string = scope.get("query_string", b"").decode()
        qs = parse_qs(query_string)
        token = qs.get("token", [None])[0]

        # Attach user to scope
        scope["user"] = await get_user_from_token(token) if token else None

        # Call the inner application
        return await self.app(scope, receive, send)

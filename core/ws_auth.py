# core/ws_auth.py
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

jwt_auth = JWTAuthentication()

@sync_to_async
def _get_user_from_token(token: str):
    validated = jwt_auth.get_validated_token(token)
    return jwt_auth.get_user(validated)

class TokenAuthMiddleware:
    """
    Channels middleware that authenticates WebSocket connects with a JWT.

    Looks for:
      - Authorization: Bearer <token>
      - ?token=<token> (also accepts 'Bearer <token>')
    Sets scope['user'] to the authenticated user (or leaves it as-is if already set).
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # If user is already set by session auth, keep it.
        user = scope.get("user", AnonymousUser())

        token = None

        # 1) Authorization header
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization")
        if auth:
            try:
                auth_str = auth.decode()
                if auth_str.lower().startswith("bearer "):
                    token = auth_str.split(" ", 1)[1].strip()
            except Exception:
                pass

        # 2) Query string ?token=...
        if not token:
            try:
                qs = parse_qs((scope.get("query_string") or b"").decode())
                t = (qs.get("token") or [None])[0]
                if t:
                    token = t.split(" ", 1)[-1].strip()  # accepts 'Bearer xxx' or 'xxx'
            except Exception:
                pass

        # Validate token if we have one and user is anonymous (or force override)
        if token and (not user or getattr(user, "is_anonymous", True)):
            try:
                user = await _get_user_from_token(token)
                scope["user"] = user
            except Exception:
                # invalid token -> keep anonymous
                pass

        return await self.inner(scope, receive, send)

# <PROJECT>/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django_asgi_app = get_asgi_application()

from assets.routing import websocket_urlpatterns
from core.ws_auth import TokenAuthMiddleware  # <-- import the middleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        TokenAuthMiddleware(              # session auth first, then JWT
            URLRouter(websocket_urlpatterns)
        )
    ),
})

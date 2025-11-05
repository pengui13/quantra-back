# assets/routing.py
from django.urls import path
from .consumers import BalanceStreamConsumer

websocket_urlpatterns = [
    path("ws/balances/", BalanceStreamConsumer.as_asgi()),
]

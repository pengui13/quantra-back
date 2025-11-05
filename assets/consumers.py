# app_name/consumers.py
import asyncio
import contextlib
from decimal import Decimal, ROUND_DOWN

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from urllib.parse import parse_qs

from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AnonymousUser

from assets.models import Balance, Quote

DECIMAL_PLACES = Decimal("0.01")
jwt_auth = JWTAuthentication()


class BalanceStreamConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # Try session auth first (AuthMiddlewareStack)
        user = self.scope.get("user")

        # If anonymous, try to authenticate via JWT (Authorization header or ?token=)
        if not user or getattr(user, "is_anonymous", True):
            token = self._extract_bearer_from_headers() or self._extract_token_from_query()
            if token:
                user = await self._authenticate_token(token)

        if not user or getattr(user, "is_anonymous", True):
            await self.close(code=4001)
            return

        self.user = user
        await self.accept()
        self._task = asyncio.create_task(self._loop_push())

    async def disconnect(self, code):
        with contextlib.suppress(Exception):
            self._task.cancel()

    async def _loop_push(self):
        try:
            while True:
                value_str = await self._compute_total_value_usdt(self.user.id)
                await self.send_json({"value": value_str})
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    # -------- auth helpers --------
    def _extract_bearer_from_headers(self):
        """
        Reads 'authorization' header from ASGI scope headers.
        Returns raw JWT string or None.
        """
        headers = dict(self.scope.get("headers") or [])
        auth = headers.get(b"authorization")
        if not auth:
            return None
        try:
            s = auth.decode().strip()
            if s.lower().startswith("bearer "):
                return s.split(" ", 1)[1].strip()
        except Exception:
            return None
        return None

    def _extract_token_from_query(self):
        """
        Allows ws://.../ws/balances/?token=<JWT> (or 'Bearer <JWT>').
        """
        try:
            qs = (self.scope.get("query_string") or b"").decode()
            token = (parse_qs(qs).get("token") or [None])[0]
            if not token:
                return None
            return token.split(" ", 1)[-1].strip()
        except Exception:
            return None

    @sync_to_async
    def _authenticate_token(self, token: str):
        """
        Validates JWT using DRF SimpleJWT and returns the user.
        """
        try:
            validated = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated)
        except Exception:
            return AnonymousUser()

    # -------- data logic --------
    @sync_to_async
    def _compute_total_value_usdt(self, user_id: int) -> str:
        """
        Sum over user's balances:
            sum( available(asset) * latest_quote(asset).value_in_usd )
        Return as string with 2 decimals (USDT-style).
        """
        total = Decimal("0")

        balances = (
            Balance.objects
            .select_related("asset")
            .filter(user_id=user_id)
            .only("available", "asset_id")
        )

        for bal in balances:
            q = (
                Quote.objects
                .filter(asset_id=bal.asset_id)
                .order_by("-time")
                .only("value_in_usd")
                .first()
            )
            if not q or q.value_in_usd is None:
                continue

            try:
                avail = Decimal(bal.available)
                px = Decimal(q.value_in_usd)
            except Exception:
                continue

            total += (avail * px)

        return str(total.quantize(DECIMAL_PLACES, rounding=ROUND_DOWN))

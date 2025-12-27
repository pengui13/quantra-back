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
        user = self.scope.get("user")

        # Try JWT if anonymous
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
                payload = await self._compute_total_value_with_rate(self.user.id)
                await self.send_json(payload)
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    # -------- auth helpers --------
    def _extract_bearer_from_headers(self):
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
        try:
            validated = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated)
        except Exception:
            return AnonymousUser()

    # -------- data logic --------
    @sync_to_async
    def _compute_total_value_with_rate(self, user_id: int) -> dict:
        """
        Compute total balances in user's preferred currency.
        Returns: { value: "123.45", currency: "EUR" }
        """
        from users.models import User  # import user model here

        total_usd = Decimal("0")

        # sum all balances in USD
        balances = (
            Balance.objects.select_related("asset")
            .filter(user_id=user_id)
            .only("available", "asset_id")
        )

        for bal in balances:
            q = (
                Quote.objects.filter(asset_id=bal.asset_id)
                .order_by("-time")
                .only("value_in_usd")
                .first()
            )
            if not q or q.value_in_usd is None:
                continue
            try:
                total_usd += Decimal(bal.available) * Decimal(q.value_in_usd)
            except Exception:
                continue

        # get user's preferred fiat
        user = User.objects.filter(id=user_id).select_related("preferred_currency").first()
        fiat_asset = user.preferred_currency if user and user.preferred_currency else None

        if not fiat_asset:
            # fallback to USD
            return {
                "value": str(total_usd.quantize(DECIMAL_PLACES, rounding=ROUND_DOWN)),
                "currency": "USD",
            }

        # get latest quote for fiat asset
        fiat_quote = (
            Quote.objects.filter(asset_id=fiat_asset.id)
            .order_by("-time")
            .only("value_in_usd")
            .first()
        )

        if not fiat_quote or not fiat_quote.value_in_usd:
            rate = Decimal("1")
        else:
            rate = Decimal(fiat_quote.value_in_usd)

        # convert USD to fiat
        total_fiat = total_usd / rate


        return {
            "value": str(total_fiat.quantize(DECIMAL_PLACES, rounding=ROUND_DOWN)),
            "currency": fiat_asset.symbol,
        }

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone       
from rest_framework import serializers 
from django.db import transaction
from decimal import Decimal
from assets.models import Quote, Balance
from staking.models import StakePending, StakeTx, StakingRewards
from . import serializers 
from django.db import models


def check_balance(user, amount, symbol):
    """
    Checks if the user has enough total balance across all networks for a given asset symbol.
    Returns True if sufficient, False otherwise.
    """
    total_balance = Balance.objects.filter(user=user, asset__symbol=symbol).aggregate(
        available=models.Sum('available')
    )['available'] or 0

    return total_balance >= amount

def get_or_create_balance(asset, user):
    """
    Returns the Balance object for a given user and asset.
    Creates it if it doesn't exist (available initialized to 0).
    """
    with transaction.atomic():
        balance, created = Balance.objects.select_for_update().get_or_create(
            user=user,
            asset=asset,
            defaults={"available": 0}
        )
        return balance

class StakeAsset(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = serializers.StakeAssetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        amount = data["amount"]
        asset = serializer.context["asset"]

        with transaction.atomic():
            if not check_balance(user, amount, asset.symbol):
                return Response(
                    {"error": ["Insufficient funds"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_balance = get_or_create_balance(asset, user)
            if user_balance.available >= amount:
                user_balance.available -= amount
                user_balance.save()
            else:
                remaining = amount - user_balance.available
                user_balance.available = 0
                user_balance.save()

                other_balances = Balance.objects.select_for_update().filter(
                    user=user,
                    asset__symbol=asset.symbol
                ).exclude(pk=user_balance.pk)

                for b in other_balances:
                    if remaining <= 0:
                        break
                    deduct = min(b.available, remaining)
                    b.available -= deduct
                    b.save()
                    remaining -= deduct

            tx_pending = StakePending.objects.create(
                user=user, asset=asset, amount=amount, timestamp=timezone.now()
            )
            tx = StakeTx.objects.create(
                user=user, asset=asset, amount=amount, type="STAKE"
            )

        return Response(
            {
                "amount": format(amount, ".2f"),
                "symbol": asset.symbol,
                "timestamp": tx.timestamp,
            },
            status=status.HTTP_201_CREATED,
        )



class GetRewardBalance(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("GET", "OPTIONS", "HEAD")

    def get(self, request, *args, **options):
        user = request.user
        section = request.query_params.get("section", "staking")
        reward, hist_reward = (0, 0)

        if section == "staking":
            stake_pending = StakePending.objects.filter(user=request.user)
            stake_rewards = StakingRewards.objects.filter(user=user)
            for el in stake_rewards:
                try:
                    rate = Quote.objects.get(interval="1MIN", symbol=el.asset).lp
                except:
                    return Response(
                        {"error": "Cant find rate for asset"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                hist_reward += el.amount * rate
            for el in stake_pending:
                try:
                    rate = Quote.objects.get(interval="1MIN", symbol=el.asset).lp
                except:
                    return Response(
                        {"error": "Cant find rate for asset"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                reward += rate * el.rewards
        else:
            savings = SavingsBalance.objects.filter(user=user, earnings__gt=0)
            savings_rewards = SavingsHistory.objects.filter(user=user, type="Reward")
            if savings.exists():
                for saving in savings:
                    try:
                        rate = Quote.objects.get(
                            interval="1MIN", symbol=saving.asset
                        ).lp
                    except:
                        return Response(
                            {"error": "Cant find rate for asset"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    reward += rate * saving.earnings
            if savings_rewards.exists():
                for reward_obj in savings_rewards:
                    try:
                        rate = Quote.objects.get(
                            interval="1MIN", symbol=reward_obj.asset
                        ).lp
                    except:
                        return Response(
                            {"error": "Cant find rate for asset"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    hist_reward += rate * reward_obj.amount
        return Response(
            {
                "reward": format(Decimal(reward).normalize(), "f"),
                "hist_reward": format(Decimal(hist_reward).normalize(), "f"),
            },
            status=status.HTTP_200_OK,
        )


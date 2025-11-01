from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone       
from rest_framework import serializers 
from django.db import transaction

class StakeAsset(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("POST", "OPTIONS", "HEAD")

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = serializers.StakeAssetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        amount = data["amount"]
        asset = serializer.context["asset"]

        with transaction.atomic():

            user_balance = get_or_create_balance(asset, user)
            is_enough = user_utils.check_balance(user, amount, asset.symbol)
            if not is_enough:
                return Response(
                    {"error": ["Insufficient funds"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_balance.quantity -= amount
            user_balance.save()

            tx = StakePending.objects.create(
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


from rest_framework import exceptions, serializers
from assets.models import Asset
class StakeAssetSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=8, required=True)
    symbol = serializers.CharField(max_length=30, required=True)

    def validate_symbol(self, value):
        try:
            staking_crypto = Asset.objects.get(symbol=value.upper())
        except Asset.DoesNotExist:
            raise serializers.ValidationError("Asset not found")

        self.context["asset"] = staking_crypto  # ← remove .asset
        return value
    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError(f"Invalid amount provided")
        return amount


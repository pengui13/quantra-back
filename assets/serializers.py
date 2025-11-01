from rest_framework import serializers
from .models import Asset, Network

class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = [
            "name",
            "full_name",
            "min_deposit_amount",
            "confirmations",
            "min_deposit_time",
            "apr_low",
            "apr_high",
        ]


class AssetSerializer(serializers.ModelSerializer):
    networks = NetworkSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = ["symbol", "name", "networks"]
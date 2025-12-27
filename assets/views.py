from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Asset, Balance, Network
from .serializers import AssetSerializer
from rest_framework.permissions import IsAuthenticated
from .service import BlockChainService


from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal

from assets.models import Asset, Quote
from assets.serializers import AssetSerializer



class AssetListView(APIView):

    def get(self, request):
        section = request.query_params.get("section")
        user = request.user if request.user.is_authenticated else None
        preferred_id = user.preferred_currency_id if user else None

        if section == "stake":
            assets = (
                Asset.objects
                .filter(fiat=False, staking=True, networks__apr_high__gt=0)
                .distinct()
                .prefetch_related("networks")
            )
            serializer = AssetSerializer(assets, many=True)
            return Response(serializer.data)

        elif section == "fiat":
            assets = Asset.objects.filter(fiat=True)
            data = []

            for asset in assets:
                quote = (
                    Quote.objects
                    .filter(asset=asset)
                    .order_by("-time")
                    .first()
                )

                data.append({
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "rate": float(quote.lp) if quote else None,
                    "preferred": asset.id == preferred_id,  # ⭐ ONLY HERE
                })

            return Response(data)

        else:
            assets = Asset.objects.filter(fiat=False).prefetch_related("networks")
            serializer = AssetSerializer(assets, many=True)
            return Response(serializer.data)


class Deposit(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("GET", "OPTIONS", "HEAD")

    def get(self, request, *args, **kwargs):

        user = request.user
        symbol, network = kwargs["symbol"], kwargs["network"]

        asset = Asset.objects.get(
            symbol=symbol, fiat= False
        )
        network = Network.objects.get(
            name=network
        )
        balance,created = Balance.objects.get_or_create(user=user, asset=asset, network = network)

        if balance.public:
            return Response({'address': balance.public})
        
        blockchain = BlockChainService(symbol, network.name)
        
        address_result = blockchain.address_service.create_address()
        address, private_key = address_result

        encrypted_private = blockchain.address_service.encrypt_private_key(
            private_key=private_key
        )

        balance.public, balance.private  = address, encrypted_private
        
        #blockchain.subscribe_address(symbol, network, address)

        balance.save()

        return Response({"address": balance.public})

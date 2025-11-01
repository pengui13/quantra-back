from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Asset, Balance
from .serializers import AssetSerializer
from rest_framework.permissions import IsAuthenticated
from .service import BlockChainService


blockchain = BlockChainService()

class AssetListView(APIView):


    def get(self, request):
        assets = Asset.objects.prefetch_related("networks").all()
        section = request.query_params.get("section")

        if section == "stake":
            assets = assets.filter(networks__apr_high__gt=0).distinct()

        serializer = AssetSerializer(assets, many=True)
        return Response(serializer.data)




class Deposit(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("GET", "OPTIONS", "HEAD")

    def get(self, request, *args, **kwargs):

        user = request.user
        symbol, network = kwargs["symbol"], kwargs["network"]

        asset = Asset.objects.get(
            symbol=symbol
        )

        balance = Balance.objects.get_or_create(user=user, asset=asset, network__name = network)
        if balance.public:
            return Response({'address': balance.public})
        
        address_result = blockchain.address_service.create_address(network)
        address, private_key = address_result

        encrypted_private = blockchain.address_service.encrypt_private_key(
            private_key=private_key
        )

        balance.public = address
        balance.private = encrypted_private
 
        blockchain.subscribe_address(symbol, network, address)

        balance.save()

        return Response({"address": balance.public})

from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Asset, Balance, Network
from .serializers import AssetSerializer
from rest_framework.permissions import IsAuthenticated
from .service import BlockChainService



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

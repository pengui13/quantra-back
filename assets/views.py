from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Asset, Balance, Network
from .serializers import AssetSerializer
from rest_framework.permissions import IsAuthenticated
from .service import BlockChainService
from django.db.models.functions import Coalesce
from django.db.models import Sum, F, DecimalField
import re

from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
from rest_framework import status

from assets.models import Asset, Quote
from assets.serializers import AssetSerializer

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.response import Response
from rest_framework.views import APIView
from staking.models import StakePending, StakingRewards
from assets.models import Asset, Balance

class AssetListView(APIView):

    def get(self, request):
        section = request.query_params.get("section")
        user = request.user if request.user.is_authenticated else None
        preferred_asset = user.preferred_currency if user else None

        # =========================
        # WITHDRAW SECTION
        # =========================
        if section == "withdraw":
            if not user:
                return Response([])

            assets = (
                Asset.objects
                .filter(
                    balances__user=user,
                    balances__available__gt=0
                )
                .annotate(
                    total_balance=Coalesce(
                        Sum("balances__available"),
                        0,
                        output_field=DecimalField(max_digits=20, decimal_places=8)
                    )
                )
                .distinct()
                .prefetch_related("networks")
            )

            data = []

            for asset in assets:
                asset_quote = (
                    Quote.objects
                    .filter(asset=asset)
                    .order_by("-time")
                    .first()
                )

                preferred_quote = None
                if preferred_asset:
                    preferred_quote = (
                        Quote.objects
                        .filter(asset=preferred_asset)
                        .order_by("-time")
                        .first()
                    )

                value_usd = (
                    asset.total_balance * asset_quote.value_in_usd
                    if asset_quote else 0
                )

                value_preferred = (
                    value_usd / preferred_quote.value_in_usd
                    if preferred_quote and preferred_quote.value_in_usd else None
                )

                networks_data = [
                    {
                        "id": network.id,
                        "name": network.name,
                        "min_withdrawal": str(network.min_withdrawal) if hasattr(network, 'min_withdrawal') else None,
                        "max_withdrawal": str(network.max_withdrawal) if hasattr(network, 'max_withdrawal') else None,
                    }
                    for network in asset.networks.all()
                ]

                data.append({
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "balance": str(asset.total_balance),
                    "value_usd": float(value_usd),
                    "value_preferred": float(value_preferred) if value_preferred else None,
                    "preferred_currency": preferred_asset.symbol if preferred_asset else None,
                    "networks": networks_data,
                })

            return Response(data)

        # =========================
        # STAKING SECTION
        # =========================
        elif section == "stake":
            if not user:
                return Response([])

            assets = (
                Asset.objects
                .filter(fiat=False, staking=True, networks__apr_high__gt=0)
                .distinct()
                .prefetch_related("networks")
            )

            data = []

            for asset in assets:
                # Get user's staking balance (from StakePending model)
                staking_balance = StakePending.objects.filter(
                    user=user,
                    asset=asset
                ).aggregate(
                    total=Coalesce(Sum("amount"), 0, output_field=DecimalField(max_digits=15, decimal_places=8))
                )["total"]

                # Get user's staking rewards (from StakingRewards model)
                total_rewards = StakingRewards.objects.filter(
                    user=user,
                    asset=asset
                ).aggregate(
                    total=Coalesce(Sum("amount"), 0, output_field=DecimalField(max_digits=15, decimal_places=8))
                )["total"]

                # Get pending rewards (accumulated but not yet claimed)
                pending_rewards = StakePending.objects.filter(
                    user=user,
                    asset=asset
                ).aggregate(
                    total=Coalesce(Sum("rewards"), 0, output_field=DecimalField(max_digits=15, decimal_places=8))
                )["total"]

                # Get available balance for staking
                available_balance = (
                    Balance.objects
                    .filter(user=user, asset=asset)
                    .aggregate(
                        total=Coalesce(Sum("available"), 0, output_field=DecimalField(max_digits=20, decimal_places=8))
                    )["total"]
                )

                # Get latest quote for value calculation
                asset_quote = (
                    Quote.objects
                    .filter(asset=asset)
                    .order_by("-time")
                    .first()
                )

                value_in_usd = float(staking_balance) * float(asset_quote.value_in_usd) if asset_quote else 0

                # Get network info (APR, etc.)
                network = asset.networks.first()
                apr_low = float(network.apr_low) if network and network.apr_low else 0
                apr_high = float(network.apr_high) if network and network.apr_high else 0

                data.append({
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "full_name": asset.name,
                    "quantity": float(staking_balance),
                    "total_reward": float(total_rewards),
                    "pending_reward": float(pending_rewards),
                    "avail": float(available_balance),
                    "value": value_in_usd,
                    "networks": [
                        {
                            "id": network.id,
                            "name": network.name,
                            "apr_low": apr_low,
                            "apr_high": apr_high,
                        }
                    ] if network else [],
                })

            return Response(data)

        # =========================
        # STAKE SECTION (for asset list)
        # =========================

        # =========================
        # FIAT SECTION
        # =========================
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
                    "preferred": asset.id == user.preferred_currency_id if user else False,
                })

            return Response(data)

        # =========================
        # DEFAULT SECTION
        # =========================
        else:
            assets = Asset.objects.filter(fiat=False).prefetch_related("networks")
            return Response(AssetSerializer(assets, many=True).data)
class Deposit(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ("GET", "OPTIONS", "HEAD")

    def get(self, request, *args, **kwargs):
        user = request.user
        symbol = kwargs["symbol"]
        network_name = kwargs["network"]  # rename to network_name for clarity

        try:
            asset = Asset.objects.get(symbol=symbol, fiat=False)
        except Asset.DoesNotExist:
            return Response(
                {"success": False, "error": f"Asset '{symbol}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            network = asset.networks.get(name=network_name)
        except Network.DoesNotExist:
            return Response(
                {"success": False, "error": f"Network '{network_name}' not supported for {symbol}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        balance, created = Balance.objects.get_or_create(user=user, asset=asset, network=network)

        if balance.public:
            return Response({"address": balance.public})

        # Generate new address
        blockchain = BlockChainService(symbol, network.name)
        address_result = blockchain.address_service.create_address()
        address, private_key = address_result

        encrypted_private = blockchain.address_service.encrypt_private_key(
            private_key=private_key
        )

        balance.public = address
        balance.private = encrypted_private
        balance.save()

        return Response({"address": balance.public})


class AddressValidator:
    """Validates blockchain addresses for different cryptocurrencies"""
    
    VALIDATORS = {
        "BTC": {
            "patterns": [
                r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$",  # P2PKH (1...) and P2SH (3...)
                r"^bc1[a-z0-9]{39,59}$",  # SegWit (bc1...)
            ],
            "length": (26, 62),
        },
        "ETH": {
            "patterns": [r"^0x[a-fA-F0-9]{40}$"],
            "length": (42, 42),
        },
        "TIA": {
            "patterns": [r"^celestia1[a-z0-9]{58}$"],
            "length": (65, 65),
        },
        "ATOM": {
            "patterns": [r"^cosmos1[a-z0-9]{58}$"],
            "length": (65, 65),
        },
        "DYM": {
            "patterns": [r"^dym1[a-z0-9]{58}$"],
            "length": (62, 62),
        },
        "DOT": {
            "patterns": [r"^1[1-5a-km-zA-HJ-NP-Z]{47,48}$"],  # Substrate (1...)
            "length": (48, 50),
        },
        "TRX": {
            "patterns": [r"^T[a-km-zA-HJ-NP-Z1-9]{33}$"],
            "length": (34, 34),
        },
        "GRT": {
            "patterns": [r"^0x[a-fA-F0-9]{40}$"],  # ERC-20 token, uses Ethereum format
            "length": (42, 42),
        },
        "DOGE": {
            "patterns": [
                r"^D[a-km-zA-HJ-NP-Z1-9]{25,34}$",  # Legacy (D...)
                r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$",  # P2PKH/P2SH (1, 3)
                r"^9[a-km-zA-HJ-NP-Z1-9]{25,34}$",  # Alternate (9...)
            ],
            "length": (26, 35),
        },
        "KSM": {
            "patterns": [r"^[1-5a-km-zA-HJ-NP-Z]{47,48}$"],  # Substrate (1-5)
            "length": (47, 50),
        },
        "USDT": {
            "patterns": [
                r"^0x[a-fA-F0-9]{40}$",  # Ethereum/ERC-20
                r"^T[a-km-zA-HJ-NP-Z1-9]{33}$",  # Tron/TRC-20
            ],
            "length": (34, 42),
        },
    }

    @classmethod
    def validate(cls, symbol: str, address: str) -> dict:
        """
        Validate a blockchain address for a given cryptocurrency
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            address: Blockchain address to validate
            
        Returns:
            dict: {
                'valid': bool,
                'symbol': str,
                'address': str,
                'error': str or None
            }
        """
        if not symbol or not address:
            return {
                "valid": False,
                "symbol": symbol,
                "address": address,
                "error": "Symbol and address are required"
            }

        symbol = symbol.upper().strip()
        address = address.strip()

        # Check if symbol is supported
        if symbol not in cls.VALIDATORS:
            supported = ", ".join(sorted(cls.VALIDATORS.keys()))
            return {
                "valid": False,
                "symbol": symbol,
                "address": address,
                "error": f"Unsupported cryptocurrency. Supported: {supported}"
            }

        validator_config = cls.VALIDATORS[symbol]

        # Check length
        min_len, max_len = validator_config["length"]
        if not (min_len <= len(address) <= max_len):
            return {
                "valid": False,
                "symbol": symbol,
                "address": address,
                "error": f"Invalid address length for {symbol}. Expected {min_len}-{max_len} characters, got {len(address)}"
            }

        # Check patterns
        patterns = validator_config["patterns"]
        for pattern in patterns:
            if re.match(pattern, address):
                return {
                    "valid": True,
                    "symbol": symbol,
                    "address": address,
                    "error": None
                }

        return {
            "valid": False,
            "symbol": symbol,
            "address": address,
            "error": f"Invalid address format for {symbol}"
        }


class ValidateAddressView(APIView):
    """
    API endpoint to validate cryptocurrency addresses
    
    POST /api/validate-address/
    Body: {
        "symbol": "BTC",
        "address": "1A1z7agoat2Bt...",
        "network": "Bitcoin"  # optional
    }
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        symbol = request.data.get("symbol", "").upper().strip()
        address = request.data.get("address", "").strip()
        network = request.data.get("network")

        if not symbol or not address:
            return Response(
                {
                    "valid": False,
                    "error": "symbol and address are required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate address format
        result = AddressValidator.validate(symbol, address)

        # Additional check: verify network exists for this asset if provided
        if result["valid"] and network:
            try:
                asset = Asset.objects.get(symbol=symbol)
                if not asset.networks.filter(name=network).exists():
                    return Response(
                        {
                            **result,
                            "valid": False,
                            "error": f"Network '{network}' not supported for {symbol}"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Asset.DoesNotExist:
                return Response(
                    {
                        **result,
                        "valid": False,
                        "error": f"Asset {symbol} not found"
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

        return Response(result, status=status.HTTP_200_OK if result["valid"] else status.HTTP_400_BAD_REQUEST)

from django.db import transaction
from assets.models import Transaction


class WithdrawView(APIView):
    """
    Withdrawal API endpoint: aggregates user's balance across all networks for a given asset.
    """

    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        user = request.user
        data = request.data

        # Extract and normalize fields
        symbol = str(data.get("symbol", "")).upper().strip()
        address = str(data.get("address", "")).strip()
        network_name = str(data.get("network", "")).strip()  # target network to send
        amount_str = str(data.get("amount", "")).strip()

        # Validate required fields
        if not all([symbol, address, network_name, amount_str]):
            return Response(
                {"success": False, "error": "Missing required fields: symbol, address, network, amount"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate amount
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError()
        except:
            return Response(
                {"success": False, "error": "Invalid amount. Must be a positive number."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate address
        address_check = AddressValidator.validate(symbol, address)
        if not address_check.get("valid", False):
            return Response(
                {"success": False, "error": f"Invalid address format: {address_check.get('error','Unknown error')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get asset
        try:
            asset = Asset.objects.get(symbol=symbol)
        except Asset.DoesNotExist:
            return Response(
                {"success": False, "error": f"Asset {symbol} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get target network
        try:
            target_network = asset.networks.get(name=network_name)
        except Network.DoesNotExist:
            return Response(
                {"success": False, "error": f"Network '{network_name}' not supported for {symbol}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Aggregate balances across all networks
        balances = Balance.objects.select_for_update().filter(user=user, asset=asset).order_by('-available')
        total_available = sum([b.available for b in balances], Decimal('0'))

        if total_available < amount:
            return Response(
                {
                    "success": False,
                    "error": f"Insufficient balance. Available: {total_available} {symbol}",
                    "available_balance": str(total_available)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Deduct from balances, prioritizing networks with higher balance
            remaining = amount
            used_balances = []  # track balances and amounts deducted
            for bal in balances:
                if remaining <= 0:
                    break
                deduct = min(bal.available, remaining)
                bal.available -= deduct
                bal.save()
                used_balances.append((bal, deduct))
                remaining -= deduct

            # Create withdrawal transaction (record all source networks in description)
            networks_used_desc = ", ".join([f"{b.asset.symbol}/{b.network.name if b.network else 'N/A'}: {amt}" for b, amt in used_balances])
            withdrawal_tx = Transaction.objects.create(
                user=user,
                asset=asset,
                network=target_network,
                type=Transaction.WITHDRAWAL,
                amount=amount,
                from_address=", ".join([b.public for b, _ in used_balances if b.public]),
                to_address=address,
                status=Transaction.PENDING,
                timestamp=timezone.now(),
                fee=Decimal("0"),
                description=f"Withdrawal to {address} on {network_name} (sources: {networks_used_desc})"
            )

            return Response(
                {
                    "success": True,
                    "transaction_id": str(withdrawal_tx.id),
                    "symbol": symbol,
                    "amount": str(amount),
                    "address": address,
                    "network": network_name,
                    "status": withdrawal_tx.get_status_display(),
                    "timestamp": withdrawal_tx.timestamp.isoformat(),
                    "remaining_balance": str(sum([b.available for b in balances], Decimal('0'))),
                    "message": "Withdrawal initiated successfully. Please wait for confirmation."
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            transaction.set_rollback(True)
            return Response(
                {"success": False, "error": f"Failed to process withdrawal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class WithdrawalHistoryView(APIView):
    """
    Get user's withdrawal history
    
    GET /api/withdrawal-history/?symbol=ETH&limit=10
    
    Response: {
        "count": 5,
        "results": [
            {
                "transaction_id": "txn_123456",
                "symbol": "ETH",
                "amount": "0.5",
                "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f...",
                "network": "ETH",
                "status": "pending",
                "timestamp": "2025-12-28T10:30:00Z",
                "fee": "0"
            }
        ]
    }
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        symbol = request.query_params.get("symbol")
        limit = request.query_params.get("limit", 20)

        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        # Build query
        query = Transaction.objects.filter(
            user=user,
            type=Transaction.WITHDRAWAL
        ).order_by("-timestamp")

        # Filter by symbol if provided
        if symbol:
            query = query.filter(asset__symbol=symbol.upper())

        # Limit results
        transactions = query[:limit]

        data = [
            {
                "transaction_id": str(tx.id),
                "symbol": tx.asset.symbol,
                "amount": str(tx.amount),
                "address": tx.to_address,
                "network": tx.network.name,
                "status": tx.get_status_display(),
                "timestamp": tx.timestamp.isoformat(),
                "fee": str(tx.fee),
            }
            for tx in transactions
        ]

        return Response(
            {
                "count": len(data),
                "results": data
            },
            status=status.HTTP_200_OK
        )


class WithdrawalStatusView(APIView):
    """
    Get status of a specific withdrawal transaction
    
    GET /api/withdrawal-status/{transaction_id}/
    
    Response: {
        "transaction_id": "txn_123456",
        "symbol": "ETH",
        "amount": "0.5",
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f...",
        "network": "ETH",
        "status": "pending",
        "timestamp": "2025-12-28T10:30:00Z",
        "blockchain_hash": null
    }
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, transaction_id):
        user = request.user

        try:
            tx = Transaction.objects.get(
                id=transaction_id,
                user=user,
                type=Transaction.WITHDRAWAL
            )
        except Transaction.DoesNotExist:
            return Response(
                {
                    "error": "Transaction not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "transaction_id": str(tx.id),
                "symbol": tx.asset.symbol,
                "amount": str(tx.amount),
                "address": tx.to_address,
                "network": tx.network.name,
                "status": tx.get_status_display(),
                "timestamp": tx.timestamp.isoformat(),
                "fee": str(tx.fee),
                "blockchain_hash": tx.blockchain_hash,
            },
            status=status.HTTP_200_OK
        )


from django.core.management.base import BaseCommand
from assets.models import Asset, Network
from core.service import KrakenService

kraken_client = KrakenService()


class Command(BaseCommand):
    help = "Populate Assets and Networks from Kraken API with defaults (includes APR ranges)"

    def handle(self, *args, **options):
        NETWORKS = [
            {"name": "BTC", "full_name": "Bitcoin Network", "confirmations": 2, "min_deposit_amount": 0.0005, "apr_low": 0.5, "apr_high": 1.5},
            {"name": "ETH", "full_name": "Ethereum Mainnet (ERC20)", "confirmations": 12, "min_deposit_amount": 0.01, "apr_low": 3.0, "apr_high": 5.0},
            {"name": "TRX", "full_name": "Tron Network (TRC20)", "confirmations": 20, "min_deposit_amount": 5, "apr_low": 4.0, "apr_high": 6.0},
            {"name": "BSC", "full_name": "Binance Smart Chain (BEP20)", "confirmations": 15, "min_deposit_amount": 5, "apr_low": 6.0, "apr_high": 10.0},
            {"name": "DOT", "full_name": "Polkadot", "confirmations": 20, "min_deposit_amount": 1, "apr_low": 10.0, "apr_high": 15.0},
            {"name": "KSM", "full_name": "Kusama", "confirmations": 20, "min_deposit_amount": 0.1, "apr_low": 13.0, "apr_high": 18.0},
            {"name": "ATOM", "full_name": "Cosmos Hub", "confirmations": 15, "min_deposit_amount": 0.1, "apr_low": 15.0, "apr_high": 20.0},
            {"name": "TIA", "full_name": "Celestia", "confirmations": 15, "min_deposit_amount": 0.1, "apr_low": 12.0, "apr_high": 18.0},
            {"name": "DYM", "full_name": "Dymension", "confirmations": 15, "min_deposit_amount": 0.1, "apr_low": 20.0, "apr_high": 25.0},
            {"name": "GRT", "full_name": "The Graph (ERC20)", "confirmations": 12, "min_deposit_amount": 50, "apr_low": 8.0, "apr_high": 12.0},
            {"name": "DOGE", "full_name": "Dogecoin", "confirmations": 40, "min_deposit_amount": 10, "apr_low": 1.0, "apr_high": 2.0},
        ]

        # --- Populate or update Networks ---
        for net in NETWORKS:
            obj, created = Network.objects.get_or_create(
                name=net["name"],
                defaults={
                    "full_name": net["full_name"],
                    "confirmations": net["confirmations"],
                    "min_deposit_amount": net["min_deposit_amount"],
                    "apr_low": net["apr_low"],
                    "apr_high": net["apr_high"],
                },
            )

            # If exists, update fields
            if not created:
                obj.full_name = net["full_name"]
                obj.confirmations = net["confirmations"]
                obj.min_deposit_amount = net["min_deposit_amount"]
                obj.apr_low = net["apr_low"]
                obj.apr_high = net["apr_high"]
                obj.save(update_fields=[
                    "full_name",
                    "confirmations",
                    "min_deposit_amount",
                    "apr_low",
                    "apr_high",
                ])

        # --- Assets population ---
        allowed_pairs = [
            "XBTUSDT", "ETHUSDT", "TIAUSDT", "ATOMUSDT", "DYMUSDT",
            "DOTUSDT", "TRXUSDT", "GRTUSDT", "DOGEUSDT", "KSMUSDT"
        ]

        ASSET_NAMES = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "TIA": "Celestia",
            "ATOM": "Cosmos",
            "DYM": "Dymension",
            "DOT": "Polkadot",
            "TRX": "Tron",
            "GRT": "The Graph",
            "DOGE": "Dogecoin",
            "KSM": "Kusama",
            "USDT": "Tether",
        }

        ASSET_NETWORKS = {
            "BTC": ["BTC"],
            "ETH": ["ETH"],
            "TIA": ["TIA"],
            "ATOM": ["ATOM"],
            "DYM": ["DYM"],
            "DOT": ["DOT"],
            "TRX": ["TRX"],
            "GRT": ["ETH"],     # ERC20
            "DOGE": ["DOGE"],
            "KSM": ["KSM"],
            "USDT": ["ETH", "TRX"],
        }

        data = kraken_client.get_asset_pairs()["result"]

        for key in allowed_pairs:
            symbol = key.replace("USDT", "")
            if symbol == "XBT":
                symbol = "BTC"

            asset, created = Asset.objects.get_or_create(
                symbol=symbol,
                defaults={"name": ASSET_NAMES.get(symbol, symbol)}
            )

            if not created:
                asset.name = ASSET_NAMES.get(symbol, symbol)
                asset.save(update_fields=["name"])

            network_names = ASSET_NETWORKS.get(symbol, [])
            networks = Network.objects.filter(name__in=network_names)
            asset.networks.set(networks)

        # --- Ensure USDT exists with ETH + TRX networks ---
        usdt_asset, _ = Asset.objects.get_or_create(
            symbol="USDT",
            defaults={"name": ASSET_NAMES["USDT"]}
        )
        usdt_asset.name = ASSET_NAMES["USDT"]
        usdt_asset.save(update_fields=["name"])

        eth_network = Network.objects.get(name="ETH")
        trx_network = Network.objects.get(name="TRX")
        usdt_asset.networks.set([eth_network, trx_network])

        self.stdout.write(self.style.SUCCESS("✅ Assets and Networks populated or updated successfully."))

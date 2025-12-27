from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
import json
import random
import requests

from assets.models import Asset, Quote

BINANCE_URL = "https://api.binance.com/api/v3/ticker/24hr"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

TARGET_SYMBOLS = [
    "BTC", "ETH", "TIA", "ATOM", "DYM",
    "DOT", "TRX", "GRT", "DOGE", "KSM"
]

COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "TIA": "celestia",
    "ATOM": "cosmos",
    "DYM": "dymension",
    "DOT": "polkadot",
    "TRX": "tron",
    "GRT": "the-graph",
    "DOGE": "dogecoin",
    "KSM": "kusama",
}

FIAT_ASSETS = ["USD", "EUR"]


class Command(BaseCommand):
    help = "Populate or update Quote rows for TARGET_SYMBOLS + fiat (USD, EUR)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["binance", "coingecko", "json", "random"],
            default="binance",
            help="Data source. Default: binance",
        )
        parser.add_argument(
            "--json",
            dest="json_inline",
            type=str,
            help='Inline JSON: \'{"BTC":{"price":68000,"bid":67990,"ask":68010}}\'',
        )
        parser.add_argument(
            "--json-file",
            dest="json_file",
            type=str,
            help="Path to JSON file (same structure as --json).",
        )
        parser.add_argument(
            "--interval",
            dest="interval",
            default="1m",
            help="Interval label to store on Quote (default: 1m).",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=6.0,
            help="HTTP timeout seconds for public APIs (default: 6.0).",
        )

    def handle(self, *args, **opts):
        source = opts["source"]
        interval = opts["interval"]
        timeout = float(opts["timeout"])

        # --- Fetch data ---
        if source == "json":
            payload = self._load_json(opts.get("json_inline"), opts.get("json_file"))
            self._from_json(payload, interval)
        elif source == "binance":
            self._from_binance(interval, timeout)
        elif source == "coingecko":
            self._from_coingecko(interval, timeout)
        elif source == "random":
            self._from_random(interval)
        else:
            raise CommandError("Unknown source")

        # --- Add fiat assets ---
        self._populate_fiat(interval, timeout)

        self.stdout.write(self.style.SUCCESS("✅ Quotes populated or updated."))

    # ---------------- JSON ----------------
    def _load_json(self, inline, path):
        try:
            if inline:
                return json.loads(inline)
            if path:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            raise CommandError(f"Invalid JSON: {e}")
        raise CommandError("Provide --json or --json-file when --source=json")

    def _from_json(self, data, interval):
        now = timezone.now()
        for sym, info in data.items():
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                self.stdout.write(self.style.WARNING(f"Skipping {sym}: Asset not found"))
                continue

            self._create_or_update_quote(
                asset=asset,
                interval=interval,
                bid=Decimal(str(info.get("bid", info.get("price", 0)))),
                ask=Decimal(str(info.get("ask", info.get("price", 0)))),
                lp=Decimal(str(info.get("price", 0))),
                volume=Decimal(str(info.get("volume", 0))),
                time=now,
            )

    # ---------------- Binance ----------------
    def _from_binance(self, interval, timeout):
        now = timezone.now()
        try:
            r = requests.get(BINANCE_URL, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Binance fetch failed: {e}"))
            return

        for sym in TARGET_SYMBOLS:
            pair = f"{sym}USDT"
            info = next((x for x in data if x["symbol"] == pair), None)
            if not info:
                self.stdout.write(self.style.WARNING(f"{sym}USDT not found on Binance"))
                continue

            self._create_or_update_quote(
                asset=Asset.objects.get(symbol=sym),
                interval=interval,
                bid=Decimal(info["bidPrice"]),
                ask=Decimal(info["askPrice"]),
                lp=Decimal(info["lastPrice"]),
                volume=Decimal(info["volume"]),
                time=now,
            )

    # ---------------- CoinGecko ----------------
    def _from_coingecko(self, interval, timeout):
        now = timezone.now()
        ids = ",".join(COINGECKO_IDS[sym] for sym in TARGET_SYMBOLS if sym in COINGECKO_IDS)
        try:
            r = requests.get(
                COINGECKO_URL,
                params={"ids": ids, "vs_currencies": "usd", "include_24hr_vol": "true"},
                timeout=timeout
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"CoinGecko fetch failed: {e}"))
            return

        for sym in TARGET_SYMBOLS:
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                self.stdout.write(self.style.WARNING(f"Skipping {sym}: Asset not found"))
                continue
            cg_id = COINGECKO_IDS.get(sym)
            if not cg_id or cg_id not in data:
                continue
            price = Decimal(str(data[cg_id]["usd"]))
            volume = Decimal(str(data[cg_id].get("usd_24h_vol", 0)))

            self._create_or_update_quote(
                asset=asset,
                interval=interval,
                bid=price,
                ask=price,
                lp=price,
                volume=volume,
                time=now,
            )

    # ---------------- Random ----------------
    def _from_random(self, interval):
        now = timezone.now()
        base_prices = {
            "BTC": (30000, 90000),
            "ETH": (1500, 6000),
            "TIA": (2, 25),
            "ATOM": (4, 40),
            "DYM": (1, 15),
            "DOT": (3, 30),
            "TRX": (0.06, 0.25),
            "GRT": (0.05, 1.5),
            "DOGE": (0.05, 0.5),
            "KSM": (20, 120),
        }
        for sym in TARGET_SYMBOLS:
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                continue
            low, high = base_prices.get(sym, (1, 100))
            last = Decimal(f"{random.uniform(low, high):.8f}")
            vol = Decimal(f"{random.uniform(1000, 1_000_000):.8f}")
            self._create_or_update_quote(asset, interval, last, last, last, vol, now)

    # ---------------- Fiat ----------------
    def _populate_fiat(self, interval, timeout):
        now = timezone.now()

        usd_asset = Asset.objects.filter(symbol="USD").first()
        if usd_asset:
            self._create_or_update_quote(usd_asset, interval, Decimal("1"), Decimal("1"), Decimal("1"), Decimal("0"), now)

        eur_asset = Asset.objects.filter(symbol="EUR").first()
        if eur_asset:
            price = Decimal("0")
            try:
                r = requests.get(BINANCE_URL, params={"symbol": "EURUSDT"}, timeout=timeout)
                r.raise_for_status()
                d = r.json()
                price = Decimal(str(d.get("lastPrice", "0")))
            except Exception:
                price = Decimal(f"{random.uniform(0.9, 1.1):.6f}")

            self._create_or_update_quote(eur_asset, interval, price, price, price, Decimal("0"), now)

    # ---------------- Helper ----------------
    def _create_or_update_quote(self, asset, interval, bid, ask, lp, volume, time):
        high = lp * Decimal("1.05")
        low = lp * Decimal("0.95")
        Quote.objects.update_or_create(
            asset=asset,
            interval=interval,
            defaults={
                "bid": bid,
                "ask": ask,
                "lp": lp,
                "volume": volume,
                "open_price": lp,
                "high_price": high,
                "low_price": low,
                "prev_close_price": lp,
                "max_24h": high,
                "min_24h": low,
                "is_closed": False,
                "perc_24": 0.0,
                "value_in_usd": lp,
                "time": time,
            },
        )
        self.stdout.write(f"• {asset.symbol}: last={lp}")

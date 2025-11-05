from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
import json
import random
import time
import requests

from assets.models import Asset, Quote

BINANCE_URL = "https://api.binance.com/api/v3/ticker/24hr"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# Symbols you care about (must exist in Asset table)
TARGET_SYMBOLS = [
    "BTC", "ETH", "TIA", "ATOM", "DYM",
    "DOT", "TRX", "GRT", "DOGE", "KSM"
]

# CoinGecko ids for those symbols (some tickers differ)
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

class Command(BaseCommand):
    help = "Populate Quote rows for TARGET_SYMBOLS from Binance (default), CoinGecko, JSON, or random."

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

        self.stdout.write(self.style.SUCCESS("✅ Quotes populated."))

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
        """
        {
          "BTC": { "price": 68000, "bid": 67990, "ask": 68010,
                   "volume": 123.4, "open": 66000, "high": 68500,
                   "low": 65500, "prev_close": 65800 }
        }
        Only 'price' is required.
        """
        now = timezone.now()
        for sym, vals in data.items():
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                self.stdout.write(self.style.WARNING(f"Skipping {sym}: Asset not found"))
                continue

            price = Decimal(str(vals.get("price")))
            bid = Decimal(str(vals.get("bid", price)))
            ask = Decimal(str(vals.get("ask", price)))
            volume = Decimal(str(vals.get("volume", 0)))
            open_price = Decimal(str(vals.get("open", price)))
            high_price = Decimal(str(vals.get("high", price)))
            low_price = Decimal(str(vals.get("low", price)))
            prev_close = Decimal(str(vals.get("prev_close", open_price)))
            perc_24 = float(((price - open_price) / open_price) * Decimal("100")) if open_price else 0.0

            Quote.objects.create(
                asset=asset,
                interval=interval,
                bid=bid,
                ask=ask,
                lp=price,
                volume=volume,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                prev_close_price=prev_close,
                max_24h=high_price,
                min_24h=low_price,
                is_closed=False,
                perc_24=perc_24,
                value_in_usd=price,  # USDT ≈ USD
                time=now,
            )
            self.stdout.write(f"• {sym}: price={price}")

    # ---------------- Binance ----------------
    def _from_binance(self, interval, timeout):
        """
        Uses /api/v3/ticker/24hr?symbol=<SYMBOL>USDT
        """
        now = timezone.now()
        for sym in TARGET_SYMBOLS:
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                self.stdout.write(self.style.WARNING(f"Skipping {sym}: Asset not found"))
                continue

            symbol_pair = f"{sym}USDT"
            try:
                r = requests.get(BINANCE_URL, params={"symbol": symbol_pair}, timeout=timeout)
                r.raise_for_status()
                d = r.json()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Binance fetch failed for {symbol_pair}: {e}"))
                continue

            try:
                last = Decimal(str(d.get("lastPrice", "0")))
                bid = Decimal(str(d.get("bidPrice", last)))
                ask = Decimal(str(d.get("askPrice", last)))
                volume = Decimal(str(d.get("volume", "0")))
                open_price = Decimal(str(d.get("openPrice", last)))
                high_price = Decimal(str(d.get("highPrice", last)))
                low_price = Decimal(str(d.get("lowPrice", last)))
                prev_close = Decimal(str(d.get("prevClosePrice", open_price)))
                # Binance gives priceChangePercent too, but compute ourselves against open
                perc_24 = float(((last - open_price) / open_price) * Decimal("100")) if open_price else 0.0
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Parse error for {symbol_pair}: {e}"))
                continue

            Quote.objects.create(
                asset=asset,
                interval=interval,
                bid=bid or last,
                ask=ask or last,
                lp=last,
                volume=volume,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                prev_close_price=prev_close,
                max_24h=high_price,
                min_24h=low_price,
                is_closed=False,
                perc_24=perc_24,
                value_in_usd=last,  # USDT ≈ USD
                time=now,
            )
            self.stdout.write(f"• {sym}: last={last} bid={bid} ask={ask} vol24={volume}")
            time.sleep(0.15)  # small stagger to be gentle

    # ---------------- CoinGecko ----------------
    def _from_coingecko(self, interval, timeout):
        """
        Uses /simple/price with vs_currencies=usd and asks for 24h high/low and change.
        (CG doesn't give bid/ask; we set both to price).
        """
        ids = ",".join(COINGECKO_IDS[s] for s in TARGET_SYMBOLS if s in COINGECKO_IDS)
        params = {
            "ids": ids,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
            "include_24hr_high": "true",
            "include_24hr_low": "true",
        }
        try:
            r = requests.get(COINGECKO_URL, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise CommandError(f"CoinGecko fetch failed: {e}")

        now = timezone.now()
        for sym in TARGET_SYMBOLS:
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                self.stdout.write(self.style.WARNING(f"Skipping {sym}: Asset not found"))
                continue

            cg_id = COINGECKO_IDS.get(sym)
            if cg_id not in data:
                self.stdout.write(self.style.WARNING(f"CoinGecko missing {sym} ({cg_id})"))
                continue

            d = data[cg_id]
            price = Decimal(str(d.get("usd", 0)))
            high = Decimal(str(d.get("usd_24h_high", price)))
            low = Decimal(str(d.get("usd_24h_low", price)))
            # CG doesn't provide open/prev close directly; approximate open using 24h change if available
            change_pct = Decimal(str(d.get("usd_24h_change", 0)))
            # open ≈ price / (1 + change%)
            open_price = price / (Decimal("1") + (change_pct / Decimal("100"))) if change_pct else price
            prev_close = open_price
            volume = Decimal(str(d.get("usd_24h_vol", 0)))
            bid = ask = price
            perc_24 = float(change_pct)

            Quote.objects.create(
                asset=asset,
                interval=interval,
                bid=bid,
                ask=ask,
                lp=price,
                volume=volume,
                open_price=open_price,
                high_price=high,
                low_price=low,
                prev_close_price=prev_close,
                max_24h=high,
                min_24h=low,
                is_closed=False,
                perc_24=perc_24,
                value_in_usd=price,
                time=now,
            )
            self.stdout.write(f"• {sym}: price={price} (CG)")

    # ---------------- Random ----------------
    def _from_random(self, interval):
        now = timezone.now()
        for sym in TARGET_SYMBOLS:
            asset = Asset.objects.filter(symbol=sym).first()
            if not asset:
                self.stdout.write(self.style.WARNING(f"Skipping {sym}: Asset not found"))
                continue

            # crude seeded-ish base ranges
            base = {
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
            }.get(sym, (1, 100))

            last_f = random.uniform(*base)
            open_f = last_f * random.uniform(0.95, 1.05)
            high_f = max(last_f, open_f) * random.uniform(1.00, 1.05)
            low_f = min(last_f, open_f) * random.uniform(0.95, 1.00)
            vol_f = random.uniform(1000, 1_000_000)

            last = Decimal(f"{last_f:.8f}")
            bid = last
            ask = last
            volume = Decimal(f"{vol_f:.8f}")
            open_price = Decimal(f"{open_f:.8f}")
            high_price = Decimal(f"{high_f:.8f}")
            low_price = Decimal(f"{low_f:.8f}")
            prev_close = open_price
            perc_24 = float(((last - open_price) / open_price) * Decimal("100")) if open_price else 0.0

            Quote.objects.create(
                asset=asset,
                interval=interval,
                bid=bid,
                ask=ask,
                lp=last,
                volume=volume,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                prev_close_price=prev_close,
                max_24h=high_price,
                min_24h=low_price,
                is_closed=False,
                perc_24=perc_24,
                value_in_usd=last,
                time=now,
            )
            self.stdout.write(f"• {sym}: (random) last={last}")

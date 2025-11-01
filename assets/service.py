from tronpy.keys import PrivateKey
from cryptography.fernet import Fernet
from solders.keypair import Keypair
from tronpy import Tron
from bitcoin import SelectParams
from bitcoin.wallet import CBitcoinSecret, P2PKHBitcoinAddress
from eth_account import Account
from ecdsa import SigningKey, SECP256k1

from django.conf import settings
import requests
from assets.models import Balance
from decimal import Decimal
import logging
import base58
import hashlib

logger = logging.getLogger(__name__)


class BlockChainService:
    
    def __init__(self, symbol, network):

        SelectParams("mainnet")
    
        self.DUST_LIMIT_SATS = 600

        self.symbol = symbol
        self.network = network
        self.address_service = AddressService(network)
        self._tron = Tron()
        # self._tatum_base_url = settings.TATUM_BASE_URL
        # self._fernet = Fernet(settings.WALLET_ENCRYPTION_KEY.encode())
        # self._tatum_api_key = settings.TATUM_API_KEY
        # self._webhook_url = settings.WEBHOOK_URL
        # self._api_key = settings.TATUM_API_KEY
        # self._url = settings.TATUM_SUBSCRIBE_URL





    def send_tatum(self, balance, to_addr, amount: Decimal) -> str:
        asset = balance.asset
        try:

            chain = asset.fb_native_asset
            enc = balance.encrypted_private
            if isinstance(enc, str) and enc.startswith("b'"):
                enc = eval(enc)
            priv = self.fernet.decrypt(enc).decode()

            if chain in ["ETH", "MATIC", "AVAX", "BNB"]:
                if not priv.startswith("0x"):
                    priv = "0x" + priv
            elif chain == "SOL":
                pass
            else:
                priv = priv.removeprefix("0x")

            if chain in ["ETH", "MATIC", "AVAX", "BNB"]:
                expected_length = 66
                if len(priv) != expected_length:
                    raise ValueError(
                        f"Invalid private key length for {chain}: {len(priv)}, expected {expected_length}"
                    )

            elif chain == "SOL":
                if len(priv) < 64 or len(priv) > 103:
                    raise ValueError(
                        f"Invalid private key length for SOL: {len(priv)}, expected 64-103 characters"
                    )
            elif chain in ["BTC", "LTC"]:  
                if len(priv) < 51 or len(priv) > 52:
                    raise ValueError(
                        f"Invalid private key length for {chain}: {len(priv)}, expected 51-52 characters (WIF format)"
                    )
            else:
                pass

            if chain == "BTC":
                logger.info(f"BTC transaction - Amount: {amount} BTC")
                logger.info("Using automatic fee calculation")

                body = {
                    "fromAddress": [{"address": balance.address, "privateKey": priv}],
                    "to": [{"address": to_addr, "value": float(amount)}],
                }
                endpoint = "/bitcoin/transaction"

            elif chain == "LTC":  
                logger.info(f"LTC transaction - Amount: {amount} LTC")
                logger.info("Using automatic fee calculation")

                logger.info(f"LTC Address: {balance.address}")
                logger.info(f"LTC Private Key length: {len(priv)}")
                logger.info(f"LTC Private Key starts with: {priv[:2]}")

                amount_value = float(f"{amount:.8f}")

                body = {
                    "fromAddress": [{"address": balance.address, "privateKey": priv}],
                    "to": [{"address": to_addr, "value": amount_value}],
                }
                endpoint = "/litecoin/transaction"

            elif chain == "TRX":
                if asset.symbol.upper() in settings.CHAINS_MAPPING:
                    endpoint = "/tron/transaction"
                    amount_str = f"{amount:.6f}".rstrip("0").rstrip(".")
                    body = {
                        "fromPrivateKey": priv,
                        "to": to_addr,
                        "amount": amount_str,
                        "feeLimit": 100,
                    }
                else:

                    endpoint = "/tron/trc20/transaction"
                    if hasattr(asset, "fb_decimals"):
                        decimals = min(asset.fb_decimals, 8)
                    else:
                        decimals = 6
                    amount_str = f"{amount:.{decimals}f}".rstrip("0").rstrip(".")
                    body = {
                        "fromPrivateKey": priv,
                        "to": to_addr,
                        "tokenAddress": asset.fb_contract_address,
                        "amount": amount_str,
                        "feeLimit": 100,
                    }

            elif chain == "SOL":
                if asset.symbol.upper() in settings.CHAINS_MAPPING:
                    endpoint = "/solana/transaction"
                    amount_str = f"{amount:.9f}".rstrip("0").rstrip(".")
                    body = {
                        "from": balance.address,
                        "fromPrivateKey": priv,
                        "to": to_addr,
                        "amount": amount_str,
                    }
                else:
                    endpoint = "/blockchain/token/transaction"
                    if hasattr(asset, "fb_decimals"):
                        decimals = min(
                            asset.fb_decimals, 9
                        )
                    else:
                        decimals = 6
                    amount_str = f"{amount:.{decimals}f}".rstrip("0").rstrip(".")
                    body = {
                        "chain": "SOL",
                        "from": balance.address,
                        "to": to_addr,
                        "contractAddress": asset.fb_contract_address,
                        "amount": amount_str,
                        "digits": asset.fb_decimals,
                        "fromPrivateKey": priv,
                    }
            else:
                if chain not in settings.CHAINS_MAPPING:
                    raise ValueError(f"Unsupported EVM chain: {chain}")

                chain_config = settings.CHAINS_MAPPING[chain]
                chain_url = chain_config["url"]

                is_native = asset.symbol.upper() in settings.CHAINS_MAPPING

                if is_native:
                    endpoint = f"/{chain_url}/transaction"
                    amount_str = f"{amount:.8f}".rstrip("0").rstrip(".")
                    body = {
                        "fromPrivateKey": priv,
                        "to": to_addr,
                        "amount": amount_str,
                        "currency": "MATIC" if chain == "MATIC" else chain,
                    }
                    logger.info(f"Sending native {chain}: {body}")
                else:
                    if chain == "ETH":
                        endpoint = "/ethereum/erc20/transaction"
                    elif chain == "BNB":
                        endpoint = "/bsc/bep20/transaction"
                    elif chain == "MATIC":
                        endpoint = "/polygon/transaction"
                    elif chain == "AVAX":
                        endpoint = "/avalanche/erc20/transaction"
                    else:
                        raise ValueError(f"Unsupported token chain: {chain}")

              
                    if hasattr(asset, "fb_decimals"):
                        decimals = min(asset.fb_decimals, 8) 
                    else:
                        decimals = 6 if asset.symbol.upper() in ["USDT", "USDC"] else 8

                    amount_str = f"{amount:.{decimals}f}".rstrip("0").rstrip(".")
                    if not amount_str or amount_str == "":
                        amount_str = "0"

                    if chain == "MATIC":
                        currency = f"{asset.symbol.upper()}_MATIC"
                    else:
                        currency = asset.symbol.upper()

                    body = {
                        "fromPrivateKey": priv,
                        "to": to_addr,
                        "contractAddress": (
                            "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
                            if chain == "MATIC"
                            else asset.fb_contract_address
                        ),
                        "amount": amount_str,
                        "currency": currency,
                        "digits": asset.fb_decimals,
                    }
                    logger.info(f"Sending {chain} token: {body}")

            logger.info(f"Sending to endpoint: {self.tatum_base_url + endpoint}")
            logger.info(f"Request body: {body}")

            r = requests.post(
                self.tatum_base_url + endpoint,
                json=body,
                headers={"x-api-key": self.tatum_api_key},
                timeout=30,
            )

            logger.info(f"Transaction response: {r.status_code} - {r.text}")

            if r.status_code == 200:
                txid = r.json().get("txId")
                logger.info(f"Transaction successful: {txid}")
                return txid
            else:
                logger.error(f"Broadcast {chain} failed: {r.text}")
                raise RuntimeError(f"Tatum broadcast error: {r.text}")

        except Exception as e:
            logger.error(f"Exception in send_tatum for {chain}: {str(e)}")
            raise

    def subscribe_address(self, symbol, network, public_address):

        payload = {
            "type": "ADDRESS_EVENT",
            "attr": {
                "chain": (
                    "TRON"
                    if symbol == "TRX"
                    else network
                ),
                "url": self._webhook_url,
                "address": public_address,
            },
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": self._api_key,
        }

        requests.post(self._url, json=payload, headers=headers)
        return


class AddressService:

    def __init__(self, network):
        self.network = network

    
    def create_address(self):

        import os 

        if self.network.upper() == "ETH":
            return self._create_evm_address()
        elif self.network.upper() == "TRX":
            return self._create_trx_address()
        elif self.network.upper() in ['BTC', 'LTC']:
            secret = os.urandom(32)
            if self.network.upper() == 'BTC':
                return self._create_btc_address(secret)
            else:
                return self._create_ltc_address(secret)
        elif self.network.upper() == "SOL":
            return self._create_sol_address()
        
    def _create_evm_address(self):
        acct = Account.create()
        return acct.address, acct.key.hex()

    def _create_trx_address(self):
        private_key = PrivateKey.random()
        address = private_key.public_key.to_base58check_address()
        return (address, private_key.hex())

    def _create_btc_address(self, secret):
        key = CBitcoinSecret.from_secret_bytes(secret)
        addr = P2PKHBitcoinAddress.from_pubkey(key.pub)
        wif = str(key)
        return str(addr), wif
    
    def _create_ltc_address(self, secret):
        version_byte = b"\xb0"
        compressed_priv = secret + b"\x01"
        extended_key = version_byte + compressed_priv
        wif = base58.b58encode_check(extended_key).decode("utf-8")
        sk = SigningKey.from_string(secret, curve=SECP256k1)
        vk = sk.verifying_key
        x = vk.to_string()[:32]
        y = vk.to_string()[32:]
        prefix = b"\x02" if (int.from_bytes(y, "big") % 2 == 0) else b"\x03"
        compressed_pubkey = prefix + x
        h1 = hashlib.sha256(compressed_pubkey).digest()
        h2 = hashlib.new("ripemd160", h1).digest()
        payload = b"\x30" + h2
        address = base58.b58encode_check(payload).decode("utf-8")
        return address, wif

    def _create_sol_address(self):
        keypair = Keypair()
        address = str(keypair.pubkey())
        secret_key = keypair.secret()
        public_key = bytes(keypair.pubkey())
        full_keypair = secret_key + public_key
        private_key = base58.b58encode(full_keypair).decode("utf-8")
        return address, private_key


    def encrypt_private_key(self, private_key):
        cipher = Fernet(settings.WALLET_ENCRYPTION_KEY)
        encrypted_key = cipher.encrypt(private_key.encode())
        return encrypted_key

    def decrypt_private_key(self, encrypted_private_key):
        cipher = Fernet(settings.WALLET_ENCRYPTION_KEY)
        decrypted_key = cipher.decrypt(encrypted_private_key)
        return decrypted_key.decode()

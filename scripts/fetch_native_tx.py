import requests
from time import sleep
from datetime import datetime
from app import create_app
from app.models import db, Asset, WalletAddress, Transaction

# --- Configuración de APIs ---
BLOCKSTREAM_API = "https://blockstream.info/api"
ETHERSCAN_API_KEY = "DW8EN18U6YAS6MVGERXVXSZSQFVN3XPVUV"  # Reemplaza esto
ETHERSCAN_API = "https://api.etherscan.io/api"


def fetch_btc_addresses_from_latest_block():
    """Extrae direcciones desde el bloque más reciente en Blockstream."""
    latest_block = requests.get(f"{BLOCKSTREAM_API}/blocks").json()[0]['id']
    txs = requests.get(f"{BLOCKSTREAM_API}/block/{latest_block}/txs").json()
    addresses = set()
    for tx in txs:
        for vout in tx.get("vout", []):
            addr = vout.get("scriptpubkey_address")
            if addr:
                addresses.add(addr)
    return list(addresses)


def fetch_btc_transactions(address):
    url = f"{BLOCKSTREAM_API}/address/{address}/txs"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def fetch_eth_native_transactions(wallet_address):
    url = (
        f"{ETHERSCAN_API}?module=account&action=txlist"
        f"&address={wallet_address}&sort=desc&apikey={ETHERSCAN_API_KEY}"
    )
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return data["result"] if data["status"] == "1" else []


def fetch_eth_token_transactions(contract_address, wallet_address):
    url = (
        f"{ETHERSCAN_API}?module=account&action=tokentx&contractaddress={contract_address}"
        f"&address={wallet_address}&sort=desc&apikey={ETHERSCAN_API_KEY}"
    )
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return data["result"] if data["status"] == "1" else []


def process_wallets():
    app = create_app()
    with app.app_context():
        assets = Asset.query.all()
        for asset in assets:
            print(f"\n🪙 Procesando activo: {asset.Symbol}")

            # Añadir direcciones BTC automáticamente
            if asset.Symbol.upper() == "BTC":
                try:
                    addresses = fetch_btc_addresses_from_latest_block()
                    for addr in addresses[:10]:
                        exists = WalletAddress.query.filter_by(Address=addr, AssetID=asset.AssetID).first()
                        if not exists:
                            db.session.add(WalletAddress(
                                Address=addr,
                                Symbol='BTC',
                                AssetID=asset.AssetID,
                                CreatedAt=datetime.utcnow()
                            ))
                            print(f"➕ Guardada dirección BTC: {addr}")
                    db.session.commit()
                except Exception as e:
                    print(f"⚠️ Error obteniendo direcciones BTC: {e}")

            wallets = WalletAddress.query.filter_by(AssetID=asset.AssetID).all()
            for wallet in wallets:
                print(f"📬 Dirección: {wallet.Address}")
                try:
                    if asset.Symbol.upper() == "BTC":
                        txs = fetch_btc_transactions(wallet.Address)
                        for tx in txs[:10]:
                            if not Transaction.query.filter_by(TxHash=tx['txid']).first():
                                db.session.add(Transaction(
                                    AssetID=asset.AssetID,
                                    TxHash=tx['txid'],
                                    FromAddress=tx['vin'][0]['prevout'].get('scriptpubkey_address', 'unknown') if tx['vin'] else 'unknown',
                                    ToAddress=tx['vout'][0].get('scriptpubkey_address', 'unknown') if tx['vout'] else 'unknown',
                                    Amount=tx['vout'][0]['value'] / 1e8,
                                    AmountUSD=None,
                                    Timestamp=datetime.utcfromtimestamp(tx['status']['block_time'])
                                ))
                                print(f"   ✅ Tx BTC guardada: {tx['txid']}")
                        db.session.commit()
                        sleep(1.5)

                    elif asset.Symbol.upper() == "ETH" and not asset.AssetAddress:
                        txs = fetch_eth_native_transactions(wallet.Address)
                        for tx in txs[:10]:
                            if tx["value"] == "0":
                                continue
                            if not Transaction.query.filter_by(TxHash=tx['hash']).first():
                                db.session.add(Transaction(
                                    AssetID=asset.AssetID,
                                    TxHash=tx['hash'],
                                    FromAddress=tx['from'],
                                    ToAddress=tx['to'],
                                    Amount=float(tx['value']) / 1e18,
                                    AmountUSD=None,
                                    Timestamp=datetime.utcfromtimestamp(int(tx['timeStamp']))
                                ))
                                print(f"   ✅ Tx ETH guardada: {tx['hash']}")
                        db.session.commit()
                        sleep(1.5)

                    elif asset.AssetAddress and asset.Symbol.upper() != "ETH":
                        txs = fetch_eth_token_transactions(asset.AssetAddress, wallet.Address)
                        for tx in txs[:5]:
                            if not Transaction.query.filter_by(TxHash=tx['hash']).first():
                                db.session.add(Transaction(
                                    AssetID=asset.AssetID,
                                    TxHash=tx['hash'],
                                    FromAddress=tx['from'],
                                    ToAddress=tx['to'],
                                    Amount=float(tx['value']) / (10 ** int(tx['tokenDecimal'])),
                                    AmountUSD=None,
                                    Timestamp=datetime.utcfromtimestamp(int(tx['timeStamp']))
                                ))
                                print(f"   ✅ Tx Token guardada: {tx['hash']}")
                        db.session.commit()
                        sleep(1.5)

                    else:
                        print("ℹ️ Activo no soportado o sin contrato.")

                except Exception as e:
                    print(f"⚠️ Error con {wallet.Address}: {e}")
                    db.session.rollback()


if __name__ == "__main__":
    process_wallets()

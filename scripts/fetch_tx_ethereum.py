import requests
import time
from datetime import datetime
from app import create_app, db
from app.models import Asset, Transaction, WalletAddress

# Claves API (reemplaza por las tuyas reales)
BSC_API_KEY = 'KVDQ4DN4B36ZSIVF8M4B8EF2J9J8ANZFF8'
ETH_API_KEY = 'DW8EN18U6YAS6MVGERXVXSZSQFVN3XPVUV'
HELIUS_API_KEY = '6ed7ac5b-ff7d-4ce1-b503-07b8db2ba840'  # Reemplaza por tu clave real

def fetch_bep20_transactions(asset):
    print(f"🔍 [BEP-20] Procesando {asset.Symbol}")

    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": asset.AssetAddress,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": BSC_API_KEY
    }

    response = requests.get("https://api.bscscan.com/api", params=params)
    result = response.json()

    if result.get("status") != "1" or "result" not in result:
        print(f"⚠️ No se encontraron transacciones BEP-20 para {asset.Symbol}")
        return

    for tx in result["result"]:
        if Transaction.query.filter_by(TxHash=tx["hash"]).first():
            continue

        tx_obj = Transaction(
            AssetID=asset.AssetID,
            TxHash=tx["hash"],
            FromAddress=tx["from"],
            ToAddress=tx["to"],
            Amount=round(float(tx["value"]) / (10 ** int(tx["tokenDecimal"])), 18),
            Timestamp=datetime.utcfromtimestamp(int(tx["timeStamp"]))
        )
        db.session.add(tx_obj)

    db.session.commit()
    print(f"✅ Transacciones BEP-20 guardadas para {asset.Symbol}")
    time.sleep(0.3)

def fetch_erc20_transactions(asset):
    print(f"🔍 [ERC-20] Procesando {asset.Symbol}")

    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": asset.AssetAddress,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETH_API_KEY
    }

    response = requests.get("https://api.etherscan.io/api", params=params)
    result = response.json()

    if result.get("status") != "1" or "result" not in result:
        print(f"⚠️ No se encontraron transacciones ERC-20 para {asset.Symbol}")
        return

    for tx in result["result"]:
        if Transaction.query.filter_by(TxHash=tx["hash"]).first():
            continue

        tx_obj = Transaction(
            AssetID=asset.AssetID,
            TxHash=tx["hash"],
            FromAddress=tx["from"],
            ToAddress=tx["to"],
            Amount=round(float(tx["value"]) / (10 ** int(tx["tokenDecimal"])), 18),
            Timestamp=datetime.utcfromtimestamp(int(tx["timeStamp"]))
        )
        db.session.add(tx_obj)

    db.session.commit()
    print(f"✅ Transacciones ERC-20 guardadas para {asset.Symbol}")
    time.sleep(0.3)

def fetch_solana_transactions(wallet):
    print(f"🔍 [Solana] Procesando {wallet.Symbol} para {wallet.Address}")
    address = wallet.Address

    url = f"https://api.helius.xyz/v0/addresses/{address}/transactions?api-key={HELIUS_API_KEY}"

    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"⚠️ Error en la respuesta de Helius: {response.text}")
            return

        data = response.json()
        for tx in data:
            signature = tx.get("signature")
            if not signature or Transaction.query.filter_by(TxHash=signature).first():
                continue

            timestamp = tx.get("timestamp", int(time.time()))
            instructions = tx.get("instructions", [])

            for instr in instructions:
                if "parsed" in instr and instr["parsed"].get("type") == "transfer":
                    amount = float(instr["parsed"].get("info", {}).get("amount", 0)) / 1e9
                    from_addr = instr["parsed"]["info"].get("source")
                    to_addr = instr["parsed"]["info"].get("destination")

                    tx_obj = Transaction(
                        AssetID=wallet.AssetID,
                        TxHash=signature,
                        FromAddress=from_addr or "?",
                        ToAddress=to_addr or "?",
                        Amount=round(amount, 9),
                        Timestamp=datetime.utcfromtimestamp(int(timestamp))
                    )
                    db.session.add(tx_obj)

        db.session.commit()
        print(f"✅ Transacciones Solana guardadas para {wallet.Address}")
        time.sleep(0.3)

    except Exception as e:
        print(f"❌ Error procesando Solana {wallet.Address}: {e}")

def fetch_all_transactions():
    app = create_app()
    with app.app_context():
        wallet_addresses = WalletAddress.query.all()

        for wallet in wallet_addresses:
            asset = wallet.asset
            if not asset or not asset.AssetAddress or not asset.Source:
                continue

            source = asset.Source.lower()

            try:
                if source in ("bsc", "binance-smart-chain"):
                    fetch_bep20_transactions(asset)
                elif source in ("ethereum", "eth", "erc20"):
                    fetch_erc20_transactions(asset)
                elif source == "solana":
                    fetch_solana_transactions(wallet)
                else:
                    print(f"⏭️ Red no soportada aún: {source}")
            except Exception as e:
                print(f"❌ Error procesando {asset.Symbol}: {e}")

if __name__ == "__main__":
    fetch_all_transactions()

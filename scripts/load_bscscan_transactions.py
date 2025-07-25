import os

import requests
import time
from datetime import datetime
from app import create_app, db
from app.models import Transaction, WalletAddress

# Claves API
BSC_API_KEY = os.getenv("BSCSCAN_API_KEY")
ETH_API_KEY = os.getenv("ETHERSCAN_API_KEY")
POLYGON_API_KEY = os.getenv("POLYGONSCAN_API_KEY")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
BASE_API_KEY = os.getenv("BASESCAN_API_KEY")

MAX_AMOUNT = 1e30  # límite seguro para evitar desbordamiento

def process_transaction(wallet, tx):
    try:
        amount = float(tx["value"]) / (10 ** int(tx["tokenDecimal"]))
        if amount > MAX_AMOUNT:
            print(f"⚠️ Valor extremadamente grande ignorado para {wallet.Symbol}: {amount}")
            return
        if Transaction.query.filter_by(TxHash=tx["hash"]).first():
            return
        tx_obj = Transaction(
            AssetID=wallet.AssetID,
            TxHash=tx["hash"],
            FromAddress=tx["from"],
            ToAddress=tx["to"],
            Amount=round(amount, 18),
            Timestamp=datetime.utcfromtimestamp(int(tx["timeStamp"]))
        )
        db.session.add(tx_obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error procesando transacción {tx.get('hash')}: {e}")

def fetch_bep20_transactions(wallet):
    print(f"🔍 [BEP-20] {wallet.Symbol} en {wallet.Address}")
    params = {
        "module": "account",
        "action": "tokentx",
        "address": wallet.Address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": BSC_API_KEY
    }
    response = requests.get("https://api.bscscan.com/api", params=params).json()
    if response.get("status") != "1" or "result" not in response:
        print(f"⚠️ Sin transacciones BEP-20 para {wallet.Symbol}")
        return
    for tx in response["result"]:
        process_transaction(wallet, tx)
    time.sleep(0.3)

def fetch_erc20_transactions(wallet):
    print(f"🔍 [ERC-20] {wallet.Symbol} en {wallet.Address}")
    params = {
        "module": "account",
        "action": "tokentx",
        "address": wallet.Address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETH_API_KEY
    }
    response = requests.get("https://api.etherscan.io/api", params=params).json()
    if response.get("status") != "1" or "result" not in response:
        print(f"⚠️ Sin transacciones ERC-20 para {wallet.Symbol}")
        return
    for tx in response["result"]:
        process_transaction(wallet, tx)
    time.sleep(0.3)

def fetch_polygon_transactions(wallet):
    print(f"🔍 [Polygon] {wallet.Symbol} en {wallet.Address}")
    params = {
        "module": "account",
        "action": "tokentx",
        "address": wallet.Address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": POLYGON_API_KEY
    }
    response = requests.get("https://api.polygonscan.com/api", params=params).json()
    if response.get("status") != "1" or "result" not in response:
        print(f"⚠️ Sin transacciones Polygon para {wallet.Symbol}")
        return
    for tx in response["result"]:
        process_transaction(wallet, tx)
    time.sleep(0.3)

def fetch_base_transactions(wallet):
    print(f"🔍 [Base] {wallet.Symbol} en {wallet.Address}")
    params = {
        "module": "account",
        "action": "tokentx",
        "address": wallet.Address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": BASE_API_KEY
    }
    response = requests.get("https://api.basescan.org/api", params=params).json()
    if response.get("status") != "1" or "result" not in response:
        print(f"⚠️ Sin transacciones Base para {wallet.Symbol}")
        return
    for tx in response["result"]:
        process_transaction(wallet, tx)
    time.sleep(0.3)

def fetch_solana_transactions(wallet):
    print(f"🔍 [Solana] {wallet.Symbol} en {wallet.Address}")
    url = f"https://api.helius.xyz/v0/addresses/{wallet.Address}/transactions?api-key={HELIUS_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"⚠️ Error Helius: {response.text}")
            return
        data = response.json()
        for tx in data:
            signature = tx.get("signature")
            if not signature or Transaction.query.filter_by(TxHash=signature).first():
                continue
            timestamp = tx.get("timestamp", int(time.time()))
            for instr in tx.get("instructions", []):
                if "parsed" in instr and instr["parsed"].get("type") == "transfer":
                    info = instr["parsed"]["info"]
                    amount = float(info.get("amount", 0)) / 1e9
                    if amount > MAX_AMOUNT:
                        print(f"⚠️ Valor Solana demasiado grande ignorado: {amount}")
                        continue
                    tx_obj = Transaction(
                        AssetID=wallet.AssetID,
                        TxHash=signature,
                        FromAddress=info.get("source", "?"),
                        ToAddress=info.get("destination", "?"),
                        Amount=round(amount, 9),
                        Timestamp=datetime.utcfromtimestamp(timestamp)
                    )
                    try:
                        db.session.add(tx_obj)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        print(f"❌ Error guardando transacción Solana: {e}")
        time.sleep(0.3)
    except Exception as e:
        print(f"❌ Error en fetch_solana_transactions: {e}")

def fetch_all_transactions():
    app = create_app()
    with app.app_context():
        wallets = WalletAddress.query.all()
        for wallet in wallets:
            if not wallet.Address or not wallet.Source:
                continue
            source = wallet.Source.lower()
            try:
                if source in ("bsc", "binance-smart-chain"):
                    fetch_bep20_transactions(wallet)
                elif source in ("ethereum", "eth", "erc20"):
                    fetch_erc20_transactions(wallet)
                elif source in ("polygon", "matic", "polygon-pos"):
                    fetch_polygon_transactions(wallet)
                elif source == "base":
                    fetch_base_transactions(wallet)
                elif source == "solana":
                    fetch_solana_transactions(wallet)
                else:
                    print(f"⏭️ Red no soportada: {source}")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error en {wallet.Symbol} ({wallet.Address}): {e}")

if __name__ == "__main__":
    fetch_all_transactions()

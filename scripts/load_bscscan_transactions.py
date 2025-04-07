import requests
import time
from datetime import datetime
from app import create_app, db
from app.models import Asset, Transaction
from config import Config

BSC_API_KEY = 'KVDQ4DN4B36ZSIVF8M4B8EF2J9J8ANZFF8'



def fetch_token_transactions():
    app = create_app()
    with app.app_context():
        assets = Asset.query.filter(Asset.AssetAddress.isnot(None)).all()

        for asset in assets:
            print(f"🔍 Procesando transacciones para {asset.Symbol}")

            params = {
                "module": "account",
                "action": "tokentx",
                "contractaddress": asset.AssetAddress,
                "startblock": 0,
                "endblock": 99999999,
                "sort": "desc",
                "apikey": BSC_API_KEY
            }

            try:
                response = requests.get("https://api.bscscan.com/api", params=params)
                response.raise_for_status()
                result = response.json()

                if result.get("status") != "1" or "result" not in result:
                    print(f"⚠️ No se encontraron transacciones para {asset.Symbol}")
                    continue

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
                print(f"✅ Transacciones guardadas para {asset.Symbol}")
                time.sleep(0.3)

            except Exception as e:
                print(f"❌ Error en {asset.Symbol}: {e}")



if __name__ == "__main__":
    fetch_token_transactions()

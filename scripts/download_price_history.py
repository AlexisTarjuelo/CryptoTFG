import os
import requests
from app import create_app
from app.models import db, Asset

HISTORY_FOLDER = "D:\csv_historicos"
BASE_URL = "https://www.coingecko.com/price_charts/export/{id_coin}/usd.csv"

def download_price_history():
    app = create_app()

    with app.app_context():
        if not os.path.exists(HISTORY_FOLDER):
            os.makedirs(HISTORY_FOLDER)

        assets = Asset.query.filter(Asset.id_coin.isnot(None)).all()
        print(f"🔍 {len(assets)} activos encontrados con id_coin.")

        for asset in assets:
            try:
                coin_id = asset.id_coin
                if not coin_id:
                    continue

                url = BASE_URL.format(id_coin=coin_id)
                filename = f"{asset.Symbol.upper()}_{coin_id}.csv"
                filepath = os.path.join(HISTORY_FOLDER, filename)

                response = requests.get(url)

                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    print(f"✅ Guardado: {filename}")
                else:
                    print(f"⚠️ No se pudo descargar {coin_id} - Status: {response.status_code}")

            except Exception as e:
                print(f"❌ Error con {asset.Symbol} ({asset.id_coin}): {e}")
                continue  # continuar con el resto

if __name__ == "__main__":
    download_price_history()

# scripts/update_prices.py

import time
import requests
from datetime import datetime
from app import create_app, db
from app.models import Asset, AssetPrice

def update_cryptocurrency_prices():
    """Consulta la API de CoinGecko por bloques de 100 monedas y guarda precios en la BD."""
    app = create_app()
    with app.app_context():
        assets = Asset.query.filter(Asset.id_coin.isnot(None)).all()
        if not assets:
            print("⚠️ No hay activos con id_coin en la base de datos.")
            return

        all_ids = [asset.id_coin for asset in assets]
        chunk_size = 100

        for i in range(0, len(all_ids), chunk_size):
            chunk = all_ids[i:i + chunk_size]
            ids_param = ','.join(chunk)

            url = 'https://api.coingecko.com/api/v3/coins/markets'
            params = {
                'vs_currency': 'usd',
                'ids': ids_param
            }

            try:
                response = requests.get(url, params=params)
                response.encoding = 'utf-8'
                data = response.json()

                if not isinstance(data, list):
                    print(f"⚠️ Respuesta inesperada: {data}")
                    break

                for coin in data:
                    asset = Asset.query.filter_by(id_coin=coin['id']).first()
                    if asset:
                        price_record = AssetPrice(
                            AssetID=asset.AssetID,
                            PriceUSD=coin['current_price'],
                            MarketCap=coin['market_cap'],
                            TotalVolume=coin['total_volume'],
                            RecordedAt=datetime.utcnow()
                        )
                        db.session.add(price_record)

                db.session.commit()
                print(f"✅ Precios actualizados para bloque {i // chunk_size + 1}")
                time.sleep(30)

            except requests.exceptions.RequestException as e:
                print(f"❌ Error en la API: {e}")
                break

if __name__ == "__main__":
    update_cryptocurrency_prices()

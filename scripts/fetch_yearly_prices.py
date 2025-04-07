# scripts/fetch_yearly_prices.py

import requests
from datetime import datetime
from time import sleep
from app import create_app, db
from app.models import Asset, AssetPrice


def fetch_yearly_prices():
    app = create_app()

    with app.app_context():
        assets = Asset.query.filter(Asset.id_coin.isnot(None)).all()

        for asset in assets:
            try:
                print(f"📈 Obteniendo histórico anual de {asset.Name} ({asset.id_coin})...")

                url = f"https://api.coingecko.com/api/v3/coins/{asset.id_coin}/market_chart"
                params = {
                    'vs_currency': 'usd',
                    'days': '365',
                    'interval': 'daily'
                }

                response = requests.get(url, params=params)
                if response.status_code == 429:
                    print("⏳ Límite de peticiones alcanzado. Esperando 60 segundos...")
                    sleep(60)
                    continue
                elif response.status_code != 200:
                    print(f"❌ Error al obtener precios para {asset.Symbol}: {response.status_code}")
                    continue

                data = response.json()
                prices = data.get("prices", [])
                market_caps = data.get("market_caps", [])
                volumes = data.get("total_volumes", [])

                for i in range(len(prices)):
                    try:
                        timestamp, price = prices[i]
                        date = datetime.utcfromtimestamp(timestamp / 1000)

                        market_cap = market_caps[i][1] if i < len(market_caps) else None
                        volume = volumes[i][1] if i < len(volumes) else None

                        # Verificamos si ya existe un registro para esa fecha
                        exists = AssetPrice.query.filter_by(
                            AssetID=asset.AssetID,
                            RecordedAt=date
                        ).first()

                        if exists:
                            continue

                        price_record = AssetPrice(
                            AssetID=asset.AssetID,
                            PriceUSD=round(price, 8),
                            MarketCap=round(market_cap, 8) if market_cap else None,
                            TotalVolume=round(volume, 8) if volume else None,
                            RecordedAt=date
                        )
                        db.session.add(price_record)

                    except Exception as entry_error:
                        print(f"⚠️ Error con dato puntual de {asset.Symbol}: {entry_error}")
                        continue

                db.session.commit()
                print(f"✅ Precios del año guardados para {asset.Symbol}")
                sleep(5)  # Evita sobrecarga

            except Exception as e:
                print(f"⚠️ Error con {asset.Symbol}: {e}")
                db.session.rollback()
                continue


if __name__ == "__main__":
    fetch_yearly_prices()

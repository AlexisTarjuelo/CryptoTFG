# fetch_assets.py

import requests
from time import sleep
from app import create_app
from app.models import db, Asset

def fetch_assets():
    app = create_app()

    url = 'https://api.coingecko.com/api/v3/coins/markets'
    page = 1
    per_page = 250

    with app.app_context():
        while True:
            params = {
                'vs_currency': 'usd',
                'per_page': per_page,
                'page': page
            }

            try:
                response = requests.get(url, params=params)
                response.encoding = 'utf-8'
                data = response.json()

                if not isinstance(data, list):
                    print(f"⚠️ Respuesta inesperada: {data}")
                    break

                if not data:
                    print("✅ No hay más datos. Finalizado.")
                    break

                for coin in data:
                    if 'symbol' not in coin:
                        continue

                    existing = Asset.query.filter_by(Symbol=coin['symbol'].upper()).first()

                    if existing:
                        existing.LogoURL = coin.get('image')
                        db.session.add(existing)
                        print(f"🔄 Actualizado logo de {coin['name']}")
                    else:
                        asset = Asset(
                            Name=coin.get('name'),
                            Symbol=coin['symbol'].upper(),
                            id_coin=coin.get('id'),
                            Source='coingecko',
                            LogoURL=coin.get('image')
                        )
                        db.session.add(asset)
                        print(f"🆕 Añadido {coin['name']}")

                db.session.commit()
                print(f"✅ Página {page} procesada.")
                page += 1
                sleep(30)

            except Exception as e:
                print(f"❌ Error al consultar CoinGecko: {e}")
                break

if __name__ == '__main__':
    fetch_assets()

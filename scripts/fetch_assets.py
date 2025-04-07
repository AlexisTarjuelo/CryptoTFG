# scripts/fetch_assets.py

import requests
from time import sleep
from app import create_app
from app.models import db, Asset

def fetch_assets():
    app = create_app()

    url = 'https://api.coingecko.com/api/v3/coins/markets'
    page = 1
    per_page = 100

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
                    try:
                        if 'symbol' not in coin:
                            continue

                        coin_id = coin.get('id')
                        if not coin_id:
                            continue

                        # Consulta a /coins/{id} para obtener detalles y plataformas
                        coin_detail_url = f'https://api.coingecko.com/api/v3/coins/{coin_id}'
                        coin_detail_response = requests.get(coin_detail_url)
                        coin_detail = coin_detail_response.json()

                        platforms = coin_detail.get('platforms', {})

                        # Obtener la primera dirección disponible
                        contract_address = None
                        for platform, address in platforms.items():
                            if address:
                                contract_address = address
                                break

                        existing = Asset.query.filter_by(Symbol=coin['symbol'].upper()).first()

                        if existing:
                            existing.LogoURL = coin.get('image')
                            if contract_address:
                                existing.AssetAddress = contract_address
                            db.session.add(existing)
                            print(f"🔄 Actualizado {coin['name']}")
                        else:
                            asset = Asset(
                                Name=coin.get('name'),
                                Symbol=coin['symbol'].upper(),
                                id_coin=coin.get('id'),
                                Source='coingecko',
                                LogoURL=coin.get('image'),
                                AssetAddress=contract_address
                            )
                            db.session.add(asset)
                            print(f"🆕 Añadido {coin['name']}")

                        db.session.commit()
                        sleep(1)

                    except Exception as coin_error:
                        print(f"⚠️ Error con la moneda {coin.get('id', 'desconocida')}: {coin_error}")
                        db.session.rollback()
                        continue  # Continuar con la siguiente moneda

                print(f"✅ Página {page} procesada.")
                page += 1
                sleep(30)

            except Exception as page_error:
                print(f"❌ Error al procesar la página {page}: {page_error}")
                break

if __name__ == '__main__':
    fetch_assets()

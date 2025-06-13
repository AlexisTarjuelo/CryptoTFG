import requests
from time import sleep
from app import create_app
from app.models import db, Asset, WalletAddress

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
                        symbol_upper = coin['symbol'].upper()

                        # Obtener o crear el activo
                        existing = Asset.query.filter_by(Symbol=symbol_upper).first()
                        if existing:
                            existing.LogoURL = coin.get('image')
                            db.session.add(existing)
                        else:
                            existing = Asset(
                                Name=coin.get('name'),
                                Symbol=symbol_upper,
                                id_coin=coin_id,
                                Source='coingecko',
                                LogoURL=coin.get('image'),
                            )
                            db.session.add(existing)
                            db.session.flush()  # Para obtener el AssetID
                            print(f"🆕 Añadido {coin['name']} ({symbol_upper})")

                        db.session.commit()

                        # Guardar contratos en WalletAddresses por cada plataforma
                        for platform, address in platforms.items():
                            if not address:
                                continue

                            source = platform.lower()
                            if 'binance' in source:
                                source = 'bsc'
                            elif 'ethereum' in source:
                                source = 'ethereum'
                            elif 'polygon' in source:
                                source = 'polygon'

                            # Evita duplicados
                            exists = WalletAddress.query.filter_by(
                                Address=address,
                                Source=source,
                                AssetID=existing.AssetID
                            ).first()

                            if not exists:
                                wa = WalletAddress(
                                    Address=address,
                                    Symbol=symbol_upper,
                                    Source=source,
                                    AssetID=existing.AssetID
                                )
                                db.session.add(wa)
                                print(f"➕ Contrato guardado para {symbol_upper} en {source}")

                        db.session.commit()
                        sleep(1)  # evitar rate limit

                    except Exception as coin_error:
                        print(f"⚠️ Error con la moneda {coin.get('id', 'desconocida')}: {coin_error}")
                        db.session.rollback()
                        continue

                print(f"✅ Página {page} procesada.")
                page += 1
                sleep(60)  # evitar límites de CoinGecko

            except Exception as page_error:
                print(f"❌ Error al procesar la página {page}: {page_error}")
                break

if __name__ == '__main__':
    fetch_assets()

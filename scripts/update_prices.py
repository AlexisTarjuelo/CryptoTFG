# scripts/update_prices.py

import time
import requests
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app import create_app, db
from app.models import Asset, AssetPrice

def safe_decimal(value, default=0):
    """Convierte valores a Decimal, o devuelve el valor por defecto si falla."""
    try:
        return Decimal(str(value)) if value is not None else Decimal(default)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)

def update_cryptocurrency_prices():
    """Consulta CoinGecko y guarda precios y métricas adicionales en la BD."""
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
                'ids': ids_param,
                'price_change_percentage': '24h,7d,30d'
            }

            try:
                response = requests.get(url, params=params)
                response.encoding = 'utf-8'
                data = response.json()

                if not isinstance(data, list):
                    print(f"⚠️ Respuesta inesperada: {data}")
                    break

                insertados = 0
                for coin in data:
                    price_usd = coin.get('current_price')
                    if price_usd is None:
                        print(f"❌ Precio nulo para {coin.get('id')} – omitido.")
                        continue

                    asset = Asset.query.filter_by(id_coin=coin['id']).first()
                    if asset:
                        price_record = AssetPrice(
                            AssetID=asset.AssetID,
                            PriceUSD=safe_decimal(price_usd),
                            MarketCap=safe_decimal(coin.get('market_cap')),
                            TotalVolume=safe_decimal(coin.get('total_volume')),
                            FullyDilutedValuation=safe_decimal(coin.get('fully_diluted_valuation')),
                            CirculatingSupply=safe_decimal(coin.get('circulating_supply')),
                            TotalSupply=safe_decimal(coin.get('total_supply')),
                            MaxSupply=safe_decimal(coin.get('max_supply')),
                            ATH=safe_decimal(coin.get('ath')),
                            ATHDate=datetime.fromisoformat(coin['ath_date'].replace('Z', '')) if coin.get('ath_date') else None,
                            ATL=safe_decimal(coin.get('atl')),
                            ATLDate=datetime.fromisoformat(coin['atl_date'].replace('Z', '')) if coin.get('atl_date') else None,
                            PriceChange24hPct=safe_decimal(coin.get('price_change_percentage_24h')),
                            PriceChange7dPct=safe_decimal(coin.get('price_change_percentage_7d_in_currency')),
                            PriceChange30dPct=safe_decimal(coin.get('price_change_percentage_30d_in_currency')),
                            RecordedAt=datetime.utcnow()
                        )

                        db.session.add(price_record)
                        insertados += 1

                db.session.commit()
                print(f"✅ Bloque {i // chunk_size + 1}: {insertados} precios guardados.")
                time.sleep(30)

            except requests.exceptions.RequestException as e:
                print(f"❌ Error en la API: {e}")
                break
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error inesperado al guardar precios: {e}")

if __name__ == "__main__":
    update_cryptocurrency_prices()

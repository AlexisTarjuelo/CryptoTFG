import os
import pandas as pd
from datetime import datetime
from shutil import move
from app import create_app
from app.models import db, Asset, AssetPrice

CSV_FOLDER = os.path.join('D:', 'csv_historicos')
PROCESSED_FOLDER = os.path.join(CSV_FOLDER, 'Procesados', 'OK')

def load_prices_from_csv():
    app = create_app()

    with app.app_context():
        for file in os.listdir(CSV_FOLDER):
            if not file.endswith('.csv'):
                continue

            try:
                # Extraer SYMBOL e id_coin del nombre del archivo
                name_part = file.replace('.csv', '')
                symbol, coin_id = name_part.split('_')

                asset = Asset.query.filter_by(Symbol=symbol.upper(), id_coin=coin_id).first()
                if not asset:
                    print(f"⚠️ Activo no encontrado para {symbol}_{coin_id}")
                    continue

                filepath = os.path.join(CSV_FOLDER, file)
                df = pd.read_csv(filepath)

                # Verificar columnas requeridas
                required_columns = {'price', 'market_cap', 'total_volume', 'snapped_at'}
                if not required_columns.issubset(df.columns):
                    print(f"❌ Columnas faltantes en {file}")
                    continue

                # Obtener fechas ya existentes para evitar duplicados
                existing_dates = {
                    ap.RecordedAt for ap in AssetPrice.query.filter_by(AssetID=asset.AssetID).all()
                }

                registros_agregados = 0
                for idx, row in df.iterrows():
                    try:
                        recorded_at = datetime.strptime(
                            row['snapped_at'].replace(' UTC', ''), '%Y-%m-%d %H:%M:%S'
                        )
                        if recorded_at in existing_dates:
                            continue

                        price = float(row['price'])
                        market_cap = float(row['market_cap']) if not pd.isna(row['market_cap']) else None
                        volume = float(row['total_volume']) if not pd.isna(row['total_volume']) else None

                        price_record = AssetPrice(
                            AssetID=asset.AssetID,
                            PriceUSD=price,
                            MarketCap=market_cap,
                            TotalVolume=volume,
                            RecordedAt=recorded_at
                        )
                        db.session.add(price_record)
                        registros_agregados += 1

                    except Exception as inner_e:
                        print(f"⚠️ Error en fila {idx} de {file}: {inner_e}")

                if registros_agregados > 0:
                    db.session.commit()
                    print(f"✅ Cargado: {file} ({registros_agregados} nuevos registros)")
                else:
                    print(f"ℹ️ Sin nuevos registros para {file}")

                # Mover archivo procesado
                os.makedirs(PROCESSED_FOLDER, exist_ok=True)
                move(filepath, os.path.join(PROCESSED_FOLDER, file))

            except Exception as e:
                print(f"❌ Error al procesar {file}: {e}")
                db.session.rollback()

if __name__ == '__main__':
    load_prices_from_csv()

import os
import pandas as pd
from datetime import datetime
from shutil import move
from app import create_app
from app.models import db, Asset, AssetPrice

CSV_FOLDER = 'D:\csv_historicos'
PROCESSED_FOLDER = 'D:\csv_historicos/Procesados/OK'

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

                for _, row in df.iterrows():
                    try:
                        price = float(row['price'])
                        market_cap = float(row['market_cap']) if not pd.isna(row['market_cap']) else None
                        volume = float(row['total_volume']) if not pd.isna(row['total_volume']) else None
                        recorded_at = datetime.strptime(row['snapped_at'].replace(' UTC', ''), '%Y-%m-%d %H:%M:%S')

                        price_record = AssetPrice(
                            AssetID=asset.AssetID,
                            PriceUSD=price,
                            MarketCap=market_cap,
                            TotalVolume=volume,
                            RecordedAt=recorded_at
                        )
                        db.session.add(price_record)

                    except Exception as inner_e:
                        print(f"⚠️ Error en fila: {inner_e}")

                db.session.commit()
                print(f"✅ Cargado: {file}")

                # Mover archivo procesado
                os.makedirs(PROCESSED_FOLDER, exist_ok=True)
                move(filepath, os.path.join(PROCESSED_FOLDER, file))

            except Exception as e:
                print(f"❌ Error al procesar {file}: {e}")
                db.session.rollback()

if __name__ == '__main__':
    load_prices_from_csv()

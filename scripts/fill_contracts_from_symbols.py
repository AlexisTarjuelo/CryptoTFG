# store_contracts_as_wallets.py

import requests
import time
from datetime import datetime
from app import create_app, db
from app.models import Asset, WalletAddress


def get_platform_contracts(coin_id, retries=3):
    """
    Consulta CoinGecko para obtener todas las direcciones por red (platforms) de un token.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    for attempt in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 429:
                print(f"[{coin_id}] ⏳ Rate limit alcanzado. Esperando 10s...")
                time.sleep(10)
                continue
            if response.status_code != 200:
                print(f"[{coin_id}] ⚠️ Respuesta no exitosa: {response.status_code}")
                return {}
            return response.json().get("platforms", {})
        except Exception as e:
            print(f"[{coin_id}] ⚠️ Error de red: {e}")
            time.sleep(5)
    return {}


def store_contracts():
    """
    Consulta CoinGecko por cada asset con id_coin, obtiene contratos y los guarda en WalletAddresses.
    """
    app = create_app()

    with app.app_context():
        assets = Asset.query.filter(Asset.id_coin != None).all()

        for index, asset in enumerate(assets, start=1):
            coin_id = asset.id_coin
            print(f"\n🔍 Procesando {asset.Name} ({coin_id})")

            platforms = get_platform_contracts(coin_id)
            time.sleep(1.5)  # Pausa para evitar bloqueos

            if not platforms:
                print(f"[{asset.Name}] ℹ️ Sin plataformas encontradas o respuesta vacía")
                continue

            for network, contract in platforms.items():
                if not contract:
                    continue  # Omitir entradas vacías

                # ¿Ya existe esta dirección para este asset?
                exists = WalletAddress.query.filter_by(Address=contract, AssetID=asset.AssetID).first()
                if exists:
                    print(f"[{asset.Name}] 🔁 Ya registrado en {network}")
                    continue

                # Crear nueva entrada
                new_wallet = WalletAddress(
                    UserID=None,
                    Address=contract,
                    Symbol=asset.Symbol,
                    AssetID=asset.AssetID,
                    CreatedAt=datetime.utcnow()
                )
                db.session.add(new_wallet)
                print(f"[{asset.Name}] ✅ Agregado contrato en {network}: {contract}")

            db.session.commit()

            # Pausa extra cada 20 activos para evitar rate limit
            if index % 20 == 0:
                print("🛑 Pausa extendida (10s) por seguridad ante rate limit...")
                time.sleep(10)

        print("\n🎉 Todos los contratos han sido registrados como WalletAddresses.")


if __name__ == "__main__":
    store_contracts()

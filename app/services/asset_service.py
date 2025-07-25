import subprocess
import sys
import threading

from app import db
from app.models import Asset


def get_all_assets():
    return Asset.query.order_by(Asset.Name).all()


def get_asset_by_id(asset_id):
    return Asset.query.get_or_404(asset_id)


def update_asset(asset_id, data):
    asset = get_asset_by_id(asset_id)
    asset.Name = data.get('name', asset.Name)
    asset.Symbol = data.get('symbol', asset.Symbol)
    asset.AssetAddress = data.get('address', asset.AssetAddress)
    asset.Decimals = data.get('decimals', asset.Decimals)
    asset.Source = data.get('source', asset.Source)
    db.session.commit()
    return asset


def delete_asset(asset_id):
    asset = get_asset_by_id(asset_id)
    db.session.delete(asset)
    db.session.commit()
    return True


def update_assets_background():
    def run_assets():
        try:
            subprocess.run([sys.executable, 'scripts/fetch_assets.py'], check=True)
        except Exception as e:
            print(f"❌ Error actualizando activos: {e}")
    threading.Thread(target=run_assets).start()
    return True


def update_prices_background():
    def run_prices():
        try:
            subprocess.run([sys.executable, 'scripts/update_prices.py'], check=True)
        except Exception as e:
            print(f"❌ Error actualizando precios: {e}")
    threading.Thread(target=run_prices).start()
    return True

# app/services/versus_service.py

from app.models import Asset, AssetPrice
from sqlalchemy import asc
from datetime import datetime

def get_all_assets_for_versus():
    return Asset.query.with_entities(Asset.Symbol, Asset.Name, Asset.LogoURL).all()

def get_asset_by_symbol(symbol: str):
    return Asset.query.filter_by(Symbol=symbol).first()

def get_price_history(asset_id, limit=180):
    prices = (
        AssetPrice.query
        .filter_by(AssetID=asset_id)
        .order_by(AssetPrice.RecordedAt.asc())
        .limit(limit)
        .all()
    )
    return [
        [p.RecordedAt.strftime('%Y-%m-%d'), float(p.PriceUSD)]
        for p in prices if p.PriceUSD is not None
    ]

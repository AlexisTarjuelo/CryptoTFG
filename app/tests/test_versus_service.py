import pytest
from datetime import datetime, timedelta
from app import db
from app.models import Asset, AssetPrice
from app.services import versus_service


@pytest.fixture
def sample_asset(app):
    asset = Asset(
        Name="Bitcoin",
        Symbol="BTC",
        AssetAddress="0xbtc",
        Decimals=18,
        Source="manual",
        id_coin="bitcoin",
        LogoURL="btc.png"
    )
    db.session.add(asset)
    db.session.commit()
    return asset


@pytest.fixture
def sample_prices(sample_asset):
    now = datetime.utcnow()
    for i in range(5):
        price = AssetPrice(
            AssetID=sample_asset.AssetID,
            PriceUSD=30000 + i * 1000,
            RecordedAt=now - timedelta(days=i)
        )
        db.session.add(price)
    db.session.commit()


def test_get_all_assets_for_versus(sample_asset):
    result = versus_service.get_all_assets_for_versus()
    assert any(a.Symbol == sample_asset.Symbol for a in result)
    assert any(a.Name == sample_asset.Name for a in result)
    assert any(a.LogoURL == sample_asset.LogoURL for a in result)


def test_get_asset_by_symbol(sample_asset):
    asset = versus_service.get_asset_by_symbol("BTC")
    assert asset is not None
    assert asset.Symbol == "BTC"
    assert asset.Name == "Bitcoin"


def test_get_price_history(sample_asset, sample_prices):
    history = versus_service.get_price_history(sample_asset.AssetID)
    assert isinstance(history, list)
    assert len(history) == 5
    assert all(len(entry) == 2 for entry in history)  # [date, price]
    assert all(isinstance(entry[0], str) and isinstance(entry[1], float) for entry in history)

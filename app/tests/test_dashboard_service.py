import pytest
from datetime import datetime, timedelta
from app import db
from app.models import Asset, AssetPrice, PortfolioAsset
from app.services import dashboard_service


@pytest.fixture
def sample_dashboard_data(app):
    with app.app_context():
        asset = Asset(
            Name="Bitcoin",
            Symbol="BTC",
            AssetAddress="0xbtc",
            Decimals=8,
            Source="manual",
            id_coin="bitcoin",
            LogoURL="btc.png"
        )
        db.session.add(asset)
        db.session.commit()

        now = datetime.utcnow()

        prices = [
            AssetPrice(AssetID=asset.AssetID, PriceUSD=30000, MarketCap=500_000_000, TotalVolume=30_000_000, RecordedAt=now - timedelta(days=29)),
            AssetPrice(AssetID=asset.AssetID, PriceUSD=32000, MarketCap=550_000_000, TotalVolume=35_000_000, RecordedAt=now - timedelta(days=15)),
            AssetPrice(AssetID=asset.AssetID, PriceUSD=33000, MarketCap=580_000_000, TotalVolume=40_000_000, RecordedAt=now)
        ]
        db.session.add_all(prices)

        portfolio = PortfolioAsset(UserID=1, AssetID=asset.AssetID, Quantity=1.5, PurchaseValueUSD=45000, CurrentValueUSD=49500)
        db.session.add(portfolio)

        db.session.commit()
        return asset


def test_get_dashboard_data(app, sample_dashboard_data):
    with app.app_context():
        result = dashboard_service.get_dashboard_data(user_id=1, sort_by='marketcap', page=1, per_page=10)

        assert "assets" in result
        assert isinstance(result["assets"], list)
        assert result["total_value"] > 0
        assert "change_24h" in result
        assert "top_asset" in result
        assert result["page"] == 1
        assert result["sort_by"] == 'marketcap'


def test_get_market_overview(app, sample_dashboard_data):
    with app.app_context():
        result = dashboard_service.get_market_overview()
        assert result["market_cap"] > 0
        assert result["volume"] > 0




def test_generate_dashboard_csv(app, sample_dashboard_data):
    with app.app_context():
        response = dashboard_service.generate_dashboard_csv()
        assert response.status_code == 200
        assert response.mimetype == "text/csv"
        assert b"Name,Symbol,PriceUSD" in response.data

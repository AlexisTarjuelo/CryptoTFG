import pytest
from app import db
from app.models import Asset, Holder, HolderCategory
from app.services import holder_service

@pytest.fixture
def sample_holder_data(app):
    with app.app_context():
        asset = Asset(Name="Bitcoin", Symbol="BTC", AssetAddress="0xbtc", Decimals=18, Source="manual", id_coin="btc", LogoURL="btc.png")
        db.session.add(asset)
        db.session.commit()

        category = HolderCategory(Name="Whales", MinBalance=100)
        db.session.add(category)
        db.session.commit()

        holder1 = Holder(Address="0xabc", Balance=150, AssetID=asset.AssetID, CategoryID=category.CategoryID)
        holder2 = Holder(Address="0xdef", Balance=50, AssetID=asset.AssetID)
        db.session.add_all([holder1, holder2])
        db.session.commit()

        return asset, category, [holder1, holder2]

def test_get_assets_with_holders(sample_holder_data):
    assets = holder_service.get_assets_with_holders()
    assert len(assets) == 1
    assert assets[0].Symbol == "BTC"

def test_get_all_holder_categories(sample_holder_data):
    categories = holder_service.get_all_holder_categories()
    assert len(categories) == 1
    assert categories[0].Name == "Whales"

def test_get_holders_data(sample_holder_data):
    data = holder_service.get_holders_data()
    assert len(data) == 2
    assert data[0]["asset"].startswith("Bitcoin")
    assert data[0]["category"] in ["Whales", "Sin categoría"]

def test_get_holders_summary_all(sample_holder_data):
    summary = holder_service.get_holders_summary()
    assert summary["total_holders"] == 2
    assert summary["total_balance"] == 200
    assert summary["most_common_category"] in ["Whales", "Sin categoría"]

def test_get_holders_summary_filtered(sample_holder_data):
    summary = holder_service.get_holders_summary(symbol="btc", category="whales")
    assert summary["total_holders"] == 1
    assert summary["most_common_category"] == "Whales"

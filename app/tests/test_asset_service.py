import pytest
from app import db
from app.models import Asset
from app.services import asset_service


def test_create_asset(app):
    new_asset = Asset(
        Name="TestCoin",
        Symbol="TST",
        AssetAddress="0x123",
        Decimals=18,
        Source="manual",
        id_coin="testcoin",
        LogoURL="http://example.com/logo.png"
    )
    db.session.add(new_asset)
    db.session.commit()

    found = Asset.query.filter_by(Symbol="TST").first()
    assert found is not None
    assert found.Name == "TestCoin"


def test_get_all_assets(app):
    assets = asset_service.get_all_assets()
    assert isinstance(assets, list)


def test_get_asset_by_id(app):
    asset = Asset(
        Name="Sample",
        Symbol="SMP",
        AssetAddress="0xABC",
        Decimals=8,
        Source="manual",
        id_coin="sample",
        LogoURL=""
    )
    db.session.add(asset)
    db.session.commit()

    found = asset_service.get_asset_by_id(asset.AssetID)
    assert found.Symbol == "SMP"


def test_update_asset(app):
    asset = Asset(
        Name="OldName",
        Symbol="OLD",
        AssetAddress="0x456",
        Decimals=10,
        Source="manual",
        id_coin="oldcoin",
        LogoURL=""
    )
    db.session.add(asset)
    db.session.commit()

    data = {
        "name": "NewName",
        "symbol": "NEW",
        "address": "0x789",
        "decimals": 6,
        "source": "updated"
    }
    updated = asset_service.update_asset(asset.AssetID, data)
    assert updated.Name == "NewName"
    assert updated.Symbol == "NEW"


def test_delete_asset(app):
    asset = Asset(
        Name="ToDelete",
        Symbol="DEL",
        AssetAddress="0x999",
        Decimals=4,
        Source="manual",
        id_coin="deletecoin",
        LogoURL=""
    )
    db.session.add(asset)
    db.session.commit()

    result = asset_service.delete_asset(asset.AssetID)
    assert result is True
    assert Asset.query.get(asset.AssetID) is None

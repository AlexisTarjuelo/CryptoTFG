import json
import pytest
from app.models import Asset
from flask import url_for


def create_sample_asset():
    return Asset(
        Name="AssetExample",
        Symbol="EXA",
        AssetAddress="0xabc123",
        Decimals=18,
        Source="manual",
        id_coin="assetexample",
        LogoURL="https://example.com/logo.png"
    )


def test_admin_assets_view(client, app, admin_login):
    response = client.get('/admin/assets')
    assert response.status_code == 200
    assert b"Assets" in response.data or b"Activos" in response.data


def test_update_asset_route(client, app, admin_login):
    with app.app_context():
        asset = create_sample_asset()
        from app import db
        db.session.add(asset)
        db.session.commit()

        data = {
            "name": "UpdatedName",
            "symbol": "UPD",
            "address": "0xupdated",
            "decimals": 6,
            "source": "api"
        }

        response = client.post(
            f"/admin/asset/update/{asset.AssetID}",
            data=json.dumps(data),
            content_type='application/json'
        )

        assert response.status_code == 200
        assert response.json.get("success") is True

        updated = Asset.query.get(asset.AssetID)
        assert updated.Name == "UpdatedName"
        assert updated.Symbol == "UPD"


def test_delete_asset_route(client, app, admin_login):
    with app.app_context():
        asset = create_sample_asset()
        from app import db
        db.session.add(asset)
        db.session.commit()

        response = client.delete(f"/admin/asset/delete/{asset.AssetID}")
        assert response.status_code == 200
        assert response.json.get("success") is True
        assert Asset.query.get(asset.AssetID) is None

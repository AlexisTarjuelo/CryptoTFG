import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app import db
from app.models import Asset, AssetPrice, Transaction, NoticiaCripto
from app.services.asset_detail_service import get_asset_detail


@pytest.fixture
def asset_with_prices(app):
    asset = Asset(
        Name="Ethereum",
        Symbol="ETH",
        AssetAddress="0xeth",
        Decimals=18,
        Source="manual",
        id_coin="ethereum",
        LogoURL="eth.png"
    )
    db.session.add(asset)
    db.session.commit()

    # Precios históricos
    today = datetime.utcnow()
    for i in range(10):
        price = AssetPrice(
            AssetID=asset.AssetID,
            PriceUSD=Decimal("1000") + i * 10,
            MarketCap=Decimal("1000000000"),
            TotalVolume=Decimal("50000000"),
            CirculatingSupply=Decimal("1000000"),
            MaxSupply=Decimal("1200000"),
            TotalSupply=Decimal("1100000"),
            RecordedAt=today - timedelta(days=10 - i)
        )
        db.session.add(price)

    # Transacciones
    db.session.add(Transaction(
        AssetID=asset.AssetID,
        FromAddress="0xabc",
        ToAddress="0xdef",
        Quantity=Decimal("10"),
        Timestamp=today
    ))

    # Noticias
    db.session.add(NoticiaCripto(
        Titulo="Ethereum alcanza nuevo máximo",
        Contenido="Lorem ipsum...",
        Fuente="CryptoNews",
        Activo="ETH",
        FechaPublicacion=today
    ))

    db.session.commit()
    return asset




def test_get_asset_detail_insufficient_data_for_prediction(app):
    with app.app_context():
        asset = Asset(
            Name="Litecoin",
            Symbol="LTC",
            AssetAddress="0xltc",
            Decimals=18,
            Source="manual",
            id_coin="litecoin",
            LogoURL="ltc.png"
        )
        db.session.add(asset)
        db.session.commit()

        price = AssetPrice(
            AssetID=asset.AssetID,
            PriceUSD=Decimal("50"),
            MarketCap=Decimal("100000000"),
            TotalVolume=Decimal("5000000"),
            CirculatingSupply=Decimal("2000000"),
            MaxSupply=Decimal("3000000"),
            TotalSupply=Decimal("2500000"),
            RecordedAt=datetime.utcnow()
        )
        db.session.add(price)
        db.session.commit()

        result = get_asset_detail("litecoin")

        assert result["asset"].Symbol == "LTC"
        assert result["prediction_labels"] == []
        assert result["prediction_data"] == []

import pytest
from decimal import Decimal
from datetime import datetime
from app import db
from app.models import User, Asset, AssetPrice, PortfolioAsset
from app.services import portfolio_service


@pytest.fixture
def sample_user(app):
    user = User(
        FirstName="Tester",
        LastName="Example",
        Email="tester@example.com",
        Phone="123456789",
        IsAdult=True,
        AcceptedTerms=True,
        Role="user"
    )
    user.set_password("Test123$")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_asset(app):  # 👈 Se agrega 'app' aquí
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
    return asset


@pytest.fixture
def sample_price(app, sample_asset):  # 👈 También agregamos 'app'
    price = AssetPrice(
        AssetID=sample_asset.AssetID,
        PriceUSD=2000.00,
        RecordedAt=datetime.utcnow()
    )
    db.session.add(price)
    db.session.commit()
    return price


def test_add_asset_to_portfolio(sample_user, sample_asset, sample_price):
    success, error = portfolio_service.add_asset_to_portfolio(
        user_id=sample_user.UserID,
        symbol=sample_asset.Symbol,
        quantity=Decimal("2"),
        purchase_usd=Decimal("3500")
    )
    assert success
    assert error is None

    entry = PortfolioAsset.query.filter_by(UserID=sample_user.UserID).first()
    assert entry is not None
    assert entry.Quantity == Decimal("2")
    assert entry.CurrentValueUSD == Decimal("4000")  # 2 * 2000


def test_get_user_portfolio(sample_user, sample_asset, sample_price):
    # Agregar activo primero
    portfolio_service.add_asset_to_portfolio(
        user_id=sample_user.UserID,
        symbol=sample_asset.Symbol,
        quantity=Decimal("1"),
        purchase_usd=Decimal("1800")
    )

    entries = portfolio_service.get_user_portfolio(sample_user.UserID)
    assert entries
    for entry, name, symbol, logo in entries:
        assert name == sample_asset.Name
        assert symbol == sample_asset.Symbol
        assert logo == sample_asset.LogoURL
        assert entry.CurrentValueUSD > 0


def test_calculate_portfolio_summary(sample_user, sample_asset, sample_price):
    # Agregar activo primero
    portfolio_service.add_asset_to_portfolio(
        user_id=sample_user.UserID,
        symbol=sample_asset.Symbol,
        quantity=Decimal("1"),
        purchase_usd=Decimal("1800")
    )
    entries = portfolio_service.get_user_portfolio(sample_user.UserID)
    total, avg = portfolio_service.calculate_portfolio_summary(entries)

    assert total == 2000.00
    assert avg > 0


def test_delete_asset_from_portfolio(sample_user, sample_asset, sample_price):
    # Agregar activo primero
    portfolio_service.add_asset_to_portfolio(
        user_id=sample_user.UserID,
        symbol=sample_asset.Symbol,
        quantity=Decimal("1"),
        purchase_usd=Decimal("1800")
    )

    deleted = portfolio_service.delete_asset_from_portfolio(
        user_id=sample_user.UserID,
        symbol=sample_asset.Symbol
    )
    assert deleted is True

    # Debe eliminarse completamente
    entry = PortfolioAsset.query.filter_by(UserID=sample_user.UserID).first()
    assert entry is None


def test_get_portfolio_asset_list(sample_asset):
    result = portfolio_service.get_portfolio_asset_list()
    assert (sample_asset.Symbol, sample_asset.Name) in result


def test_get_asset_latest_price(sample_asset, sample_price):
    price = portfolio_service.get_asset_latest_price("ETH")
    assert price == 2000.0

    no_price = portfolio_service.get_asset_latest_price("UNKNOWN")
    assert no_price is None

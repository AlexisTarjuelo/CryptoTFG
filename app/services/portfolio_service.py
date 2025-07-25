from app import db
from app.models import PortfolioAsset, Asset, AssetPrice
from decimal import Decimal

def get_user_portfolio(user_id):
    entries = (
        db.session.query(
            PortfolioAsset,
            Asset.Name,
            Asset.Symbol,
            Asset.LogoURL
        )
        .join(Asset, PortfolioAsset.AssetID == Asset.AssetID)
        .filter(PortfolioAsset.UserID == user_id)
        .all()
    )

    for entry, _, _, _ in entries:
        latest_price = (
            AssetPrice.query
            .filter_by(AssetID=entry.AssetID)
            .order_by(AssetPrice.RecordedAt.desc())
            .first()
        )
        if latest_price:
            entry.CurrentValueUSD = float(entry.Quantity) * float(latest_price.PriceUSD)

    db.session.commit()
    return entries


def calculate_portfolio_summary(entries):
    total_value = sum(float(e.CurrentValueUSD or 0) for e, _, _, _ in entries)
    gain_loss = sum(
        ((float(e.CurrentValueUSD or 0) - float(e.PurchaseValueUSD or 0)) / float(e.PurchaseValueUSD or 1)) * 100
        for e, _, _, _ in entries
    )
    avg_gain_loss = round(gain_loss / len(entries), 2) if entries else 0
    return round(total_value, 2), avg_gain_loss


def add_asset_to_portfolio(user_id, symbol, quantity, purchase_usd):
    asset = Asset.query.filter_by(Symbol=symbol).first()
    if not asset:
        return None, "Activo no encontrado"

    latest_price = (
        AssetPrice.query
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )
    current_price = Decimal(str(latest_price.PriceUSD)) if latest_price else Decimal("1")

    existing = PortfolioAsset.query.filter_by(UserID=user_id, AssetID=asset.AssetID).first()

    if existing:
        existing.Quantity += quantity
        existing.PurchaseValueUSD += purchase_usd
        existing.CurrentValueUSD = current_price * existing.Quantity
    else:
        new_entry = PortfolioAsset(
            UserID=user_id,
            AssetID=asset.AssetID,
            Quantity=quantity,
            PurchaseValueUSD=purchase_usd,
            CurrentValueUSD=current_price * quantity
        )
        db.session.add(new_entry)

    db.session.commit()
    return True, None


def delete_asset_from_portfolio(user_id, symbol):
    asset = Asset.query.filter_by(Symbol=symbol).first()
    if not asset:
        return False

    deleted = PortfolioAsset.query.filter_by(UserID=user_id, AssetID=asset.AssetID).delete()
    db.session.commit()
    return deleted > 0


def get_portfolio_asset_list():
    return db.session.query(Asset.Symbol, Asset.Name).order_by(Asset.Name).all()


def get_asset_latest_price(symbol):
    asset = Asset.query.filter_by(Symbol=symbol.upper()).first()
    if not asset:
        return None

    latest_price = (
        AssetPrice.query
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )

    return float(latest_price.PriceUSD) if latest_price else None

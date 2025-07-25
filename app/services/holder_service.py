from app.models import Holder, Asset, HolderCategory
from sqlalchemy import func
from collections import defaultdict


def get_assets_with_holders():
    asset_ids_with_holders = (
        Holder.query
        .with_entities(Holder.AssetID)
        .group_by(Holder.AssetID)
        .having(func.count(Holder.HolderID) > 0)
        .subquery()
    )

    return (
        Asset.query
        .join(asset_ids_with_holders, Asset.AssetID == asset_ids_with_holders.c.AssetID)
        .order_by(Asset.Symbol)
        .all()
    )


def get_all_holder_categories():
    return HolderCategory.query.order_by(HolderCategory.MinBalance).all()


def get_holders_data():
    holders = (
        Holder.query
        .join(Asset, Holder.AssetID == Asset.AssetID)
        .outerjoin(HolderCategory, Holder.CategoryID == HolderCategory.CategoryID)
        .all()
    )

    return [{
        "address": h.Address,
        "balance": float(h.Balance),
        "asset": f"{h.asset.Name} ({h.asset.Symbol})",
        "symbol": h.asset.Symbol,
        "category": h.category.Name if h.category else "Sin categoría"
    } for h in holders]


def get_holders_summary(symbol=None, category=None):
    query = Holder.query.join(Asset).outerjoin(HolderCategory)

    if symbol:
        query = query.filter(Asset.Symbol.ilike(symbol))
    if category:
        query = query.filter(HolderCategory.Name.ilike(category))

    holders = query.all()

    total_holders = len(holders)
    total_balance = sum(h.Balance for h in holders)

    category_counts = {}
    for h in holders:
        cat = h.category.Name if h.category else "Sin categoría"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    most_common = max(category_counts, key=category_counts.get) if category_counts else "-"

    return {
        "total_holders": total_holders,
        "total_balance": total_balance,
        "most_common_category": most_common
    }

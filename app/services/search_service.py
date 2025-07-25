from app.models import Asset
from sqlalchemy import or_

def search_asset_by_query(query: str):
    """Busca un asset por symbol o id_coin (exact match)."""
    return Asset.query.filter(
        or_(
            Asset.Symbol.ilike(query),
            Asset.id_coin.ilike(query)
        )
    ).first()


def get_search_suggestions(query: str, limit: int = 8):
    """Sugiere assets por name, symbol o id_coin (partial match)."""
    return Asset.query.filter(
        or_(
            Asset.Name.ilike(f"%{query}%"),
            Asset.Symbol.ilike(f"%{query}%"),
            Asset.id_coin.ilike(f"%{query}%")
        )
    ).limit(limit).all()

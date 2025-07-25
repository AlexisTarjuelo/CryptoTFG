# app/services/dashboard_service.py

from datetime import datetime, timedelta
from decimal import Decimal, DivisionByZero, InvalidOperation
from collections import defaultdict
from sqlalchemy import func
from app import db
from app.models import Asset, AssetPrice, PortfolioAsset
from io import StringIO
from flask import make_response

def get_dashboard_data(user_id, sort_by, page, per_page):
    # Subconsulta: último precio por asset
    subquery = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('max_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    # Consulta base
    query = (
        db.session.query(
            Asset.AssetID,
            Asset.Name,
            Asset.Symbol,
            Asset.LogoURL,
            Asset.id_coin,
            AssetPrice.PriceUSD,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(AssetPrice, Asset.AssetID == AssetPrice.AssetID)
        .join(subquery, (AssetPrice.AssetID == subquery.c.AssetID) & (AssetPrice.RecordedAt == subquery.c.max_date))
    )

    # Ordenamiento
    if sort_by == 'price':
        query = query.order_by(AssetPrice.PriceUSD.desc())
    elif sort_by == 'volume':
        query = query.order_by(AssetPrice.TotalVolume.desc())
    else:
        query = query.order_by(AssetPrice.MarketCap.desc())

    paginated = query.paginate(page=page, per_page=per_page)

    # Cálculo del portafolio
    portfolio_assets = PortfolioAsset.query.filter_by(UserID=user_id).all()
    total_value = sum(float(p.CurrentValueUSD or 0) for p in portfolio_assets)

    change_24h = 0
    for entry in portfolio_assets:
        latest = AssetPrice.query.filter_by(AssetID=entry.AssetID).order_by(AssetPrice.RecordedAt.desc()).first()
        day_ago = AssetPrice.query.filter(
            AssetPrice.AssetID == entry.AssetID,
            AssetPrice.RecordedAt <= datetime.utcnow() - timedelta(hours=24)
        ).order_by(AssetPrice.RecordedAt.desc()).first()

        if latest and day_ago and day_ago.PriceUSD:
            try:
                price_diff = Decimal(latest.PriceUSD) - Decimal(day_ago.PriceUSD)
                change_24h += price_diff * Decimal(entry.Quantity)
            except:
                continue

    change_24h = float(change_24h)

    # Sparkline de 7 días
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    asset_ids = [a[0] for a in paginated.items]

    price_data = (
        db.session.query(AssetPrice.AssetID, AssetPrice.RecordedAt, AssetPrice.PriceUSD)
        .filter(AssetPrice.AssetID.in_(asset_ids))
        .filter(AssetPrice.RecordedAt >= seven_days_ago)
        .order_by(AssetPrice.AssetID, AssetPrice.RecordedAt.asc())
        .all()
    )

    sparkline_map = defaultdict(list)
    for aid, dt, price in price_data:
        if price is not None:
            sparkline_map[aid].append((dt.strftime('%Y-%m-%d'), float(price)))

    enriched_assets = []
    for a in paginated.items:
        asset_id = a[0]
        sparkline = sparkline_map.get(asset_id, [])
        if sparkline and len(sparkline) >= 2:
            price_start = sparkline[0][1]
            price_end = sparkline[-1][1]
            price_change_percent = ((price_end - price_start) / price_start) * 100 if price_start else 0
        else:
            price_change_percent = 0
        enriched_assets.append((*a, sparkline, price_change_percent))

    top_asset = max(paginated.items, key=lambda x: float(x[6]) if x[6] else 0) if paginated.items else None

    return {
        "assets": enriched_assets,
        "total_value": round(total_value, 2),
        "change_24h": round(change_24h, 2),
        "top_asset": top_asset,
        "page": page,
        "total_pages": paginated.pages,
        "sort_by": sort_by
    }

def get_market_overview():
    from app.models import AssetPrice

    latest_dates = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('latest_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    latest_prices = (
        db.session.query(
            AssetPrice.AssetID,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(
            latest_dates,
            (AssetPrice.AssetID == latest_dates.c.AssetID) &
            (AssetPrice.RecordedAt == latest_dates.c.latest_date)
        )
        .all()
    )

    total_market_cap = sum(float(p.MarketCap or 0) for p in latest_prices)
    total_volume = sum(float(p.TotalVolume or 0) for p in latest_prices)

    return {
        "market_cap": total_market_cap,
        "volume": total_volume
    }

def get_market_history():
    from sqlalchemy import cast, Date
    from app.models import AssetPrice
    today = datetime.utcnow().date()
    last_30_days = today - timedelta(days=30)

    latest_per_day = (
        db.session.query(
            AssetPrice.AssetID,
            cast(AssetPrice.RecordedAt, Date).label('day'),
            func.max(AssetPrice.RecordedAt).label('latest_time')
        )
        .filter(cast(AssetPrice.RecordedAt, Date) >= last_30_days)
        .group_by(AssetPrice.AssetID, cast(AssetPrice.RecordedAt, Date))
        .subquery()
    )

    latest_prices = (
        db.session.query(
            cast(AssetPrice.RecordedAt, Date).label("day"),
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(
            latest_per_day,
            (AssetPrice.AssetID == latest_per_day.c.AssetID) &
            (cast(AssetPrice.RecordedAt, Date) == latest_per_day.c.day) &
            (AssetPrice.RecordedAt == latest_per_day.c.latest_time)
        )
        .filter(cast(AssetPrice.RecordedAt, Date) >= last_30_days)
        .order_by(cast(AssetPrice.RecordedAt, Date).asc())
        .all()
    )

    from collections import defaultdict
    daily = defaultdict(lambda: {"market_cap": 0, "volume": 0})

    for day, mcap, vol in latest_prices:
        if mcap:
            daily[day]["market_cap"] += float(mcap)
        if vol:
            daily[day]["volume"] += float(vol)

    sorted_days = sorted(daily.keys())
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in sorted_days],
        "market_cap": [daily[d]["market_cap"] for d in sorted_days],
        "volume": [daily[d]["volume"] for d in sorted_days]
    }
def generate_dashboard_csv():
    # Subconsulta para obtener la última fecha por asset
    subquery = (
        db.session.query(
            AssetPrice.AssetID,
            func.max(AssetPrice.RecordedAt).label('max_date')
        )
        .group_by(AssetPrice.AssetID)
        .subquery()
    )

    # Consulta de datos actualizados
    query = (
        db.session.query(
            Asset.Name,
            Asset.Symbol,
            AssetPrice.PriceUSD,
            AssetPrice.MarketCap,
            AssetPrice.TotalVolume
        )
        .join(AssetPrice, Asset.AssetID == AssetPrice.AssetID)
        .join(subquery, (AssetPrice.AssetID == subquery.c.AssetID) & (AssetPrice.RecordedAt == subquery.c.max_date))
        .order_by(AssetPrice.MarketCap.desc())
    )

    # Construcción CSV
    csv_output = StringIO()
    csv_output.write('Name,Symbol,PriceUSD,MarketCap,TotalVolume\n')
    for name, symbol, price, marketcap, volume in query:
        price = price or 0
        marketcap = marketcap or 0
        volume = volume or 0
        csv_output.write(f'{name},{symbol},{price},{marketcap},{volume}\n')

    # Crear respuesta Flask
    response = make_response(csv_output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename="dashboard_export.csv"'
    response.mimetype = 'text/csv'
    return response
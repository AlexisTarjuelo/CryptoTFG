# app/services/asset_detail_service.py

from datetime import datetime, timedelta
from decimal import Decimal, DivisionByZero, InvalidOperation
from app import db
from app.models import Asset, AssetPrice, Transaction, CryptoNews
import numpy as np


def get_asset_detail(id_coin):
    asset = Asset.query.filter_by(id_coin=id_coin).first_or_404()

    # Último precio
    latest_price = (
        db.session.query(AssetPrice)
        .filter_by(AssetID=asset.AssetID)
        .order_by(AssetPrice.RecordedAt.desc())
        .first()
    )

    # Historial de precios para gráfico
    price_history = [
        (p.RecordedAt.strftime("%Y-%m-%d"), float(p.PriceUSD))
        for p in (
            db.session.query(AssetPrice.RecordedAt, AssetPrice.PriceUSD)
            .filter(AssetPrice.AssetID == asset.AssetID)
            .order_by(AssetPrice.RecordedAt.asc())
            .all()
        )
    ]

    # Predicción polinómica
    prediction_labels = []
    prediction_data = []
    if len(price_history) >= 7:
        try:
            from sklearn.linear_model import LinearRegression
            from sklearn.preprocessing import PolynomialFeatures

            X = np.arange(len(price_history)).reshape(-1, 1)
            y = np.array([p[1] for p in price_history])

            poly = PolynomialFeatures(degree=3)
            X_poly = poly.fit_transform(X)
            model = LinearRegression().fit(X_poly, y)

            future_X = np.arange(len(price_history), len(price_history) + 30).reshape(
                -1, 1
            )
            future_X_poly = poly.transform(future_X)
            future_y = model.predict(future_X_poly)

            prediction_data = future_y.tolist()
            prediction_labels = [
                (datetime.utcnow().date() + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(1, 31)
            ]
        except Exception as e:
            print(f"❌ Error en predicción: {e}")

    # Valores generales
    max_supply = latest_price.MaxSupply if latest_price else None
    circulating_supply = latest_price.CirculatingSupply if latest_price else None
    total_supply = latest_price.TotalSupply if latest_price else None
    market_cap = latest_price.MarketCap if latest_price else None

    if max_supply == 0:
        max_supply = None

    # FDV
    fdv = None
    fdv_infinite = False
    if market_cap and circulating_supply:
        if max_supply:
            try:
                fdv = market_cap * (Decimal(max_supply) / Decimal(circulating_supply))
            except (DivisionByZero, InvalidOperation):
                fdv = None
        else:
            fdv_infinite = True

    # Volumen / Market Cap
    vol_mkt_cap = (
        latest_price.TotalVolume / latest_price.MarketCap * Decimal(100)
        if latest_price and latest_price.TotalVolume and latest_price.MarketCap
        else None
    )

    # 🔁 Transacciones recientes
    transactions = (
        Transaction.query.filter_by(AssetID=asset.AssetID)
        .order_by(Transaction.Timestamp.desc())
        .limit(10)
        .all()
    )

    # 🗞️ Noticias relacionadas
    related_news = (
        CryptoNews.query.filter_by(Asset=asset.Symbol)
        .order_by(CryptoNews.PublicationDate.desc())
        .limit(6)
        .all()
    )

    return {
        "asset": asset,
        "latest_price": latest_price,
        "price_history": price_history,
        "prediction_labels": prediction_labels,
        "prediction_data": prediction_data,
        "transactions": transactions,
        "fdv": fdv,
        "fdv_infinite": fdv_infinite,
        "vol_mkt_cap": vol_mkt_cap,
        "max_supply": max_supply,
        "total_supply": total_supply,
        "circulating_supply": circulating_supply,
        "related_news": related_news,
    }

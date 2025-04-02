# app/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Asset(db.Model):
    __tablename__ = 'Assets'

    AssetID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AssetAddress = db.Column(db.String(200), nullable=True)
    Name = db.Column(db.String(255), nullable=True)
    Symbol = db.Column(db.String(40), unique=True, nullable=False)
    Decimals = db.Column(db.Integer, nullable=True)
    Source = db.Column(db.String(50), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    id_coin = db.Column(db.String(100), nullable=True)
    LogoURL = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Asset {self.Symbol}>"

class AssetPrice(db.Model):
    __tablename__ = 'AssetPrices'

    PriceID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    RecordedAt = db.Column(db.DateTime, nullable=False)
    PriceUSD = db.Column(db.Numeric(18, 8), nullable=False)
    MarketCap = db.Column(db.Numeric(38, 18))
    TotalVolume = db.Column(db.Numeric(38, 18))

    # Relación hacia la tabla de Assets (opcional si necesitas acceder desde AssetPrice a Asset)
    asset = db.relationship('Asset', backref=db.backref('prices', lazy=True))

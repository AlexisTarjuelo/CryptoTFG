# app/models.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  # ❗ Importa la instancia compartida desde __init__.py

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
    LogoURL = db.Column(db.String(1000), nullable=True)

    prices = db.relationship('AssetPrice', backref='asset', lazy=True)
    transactions = db.relationship('Transaction', backref='asset', lazy=True)


class AssetPrice(db.Model):
    __tablename__ = 'AssetPrices'

    PriceID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    RecordedAt = db.Column(db.DateTime, nullable=False)
    PriceUSD = db.Column(db.Numeric(18, 8), nullable=False)
    MarketCap = db.Column(db.Numeric(38, 18))
    TotalVolume = db.Column(db.Numeric(38, 18))


class Transaction(db.Model):
    __tablename__ = 'Transactions'

    TransactionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    TxHash = db.Column(db.String(100), unique=True, nullable=False)
    FromAddress = db.Column(db.String(42), nullable=False)
    ToAddress = db.Column(db.String(42), nullable=False)
    Amount = db.Column(db.Numeric(38, 18), nullable=False)
    AmountUSD = db.Column(db.Numeric(38, 18), nullable=True)
    Timestamp = db.Column(db.DateTime, nullable=False, default=db.func.now())


# Modelo para el Usuario
class User(db.Model):
    __tablename__ = 'Users'

    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    FirstName = db.Column(db.String(100), nullable=False)
    LastName = db.Column(db.String(100), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    Phone = db.Column(db.String(15), nullable=False)
    IsAdult = db.Column(db.Boolean, default=False)
    AcceptedTerms = db.Column(db.Boolean, default=False)
    PasswordHash = db.Column(db.String(500), nullable=False)
    Role = db.Column(db.String(10), default='user', nullable=False)

    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)
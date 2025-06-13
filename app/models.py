# app/models.py

import os
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from . import db  # Importa la instancia compartida desde __init__.py


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
    Avatar = db.Column(db.String(200), nullable=False, default='dino1.png')

    # Biometría
    BiometricCredentialID = db.Column(db.String(500), nullable=True)
    BiometricPublicKey = db.Column(db.String(2000), nullable=True)
    SignCount = db.Column(db.Integer, default=0)

    # 2FA
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)

    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)

    def generate_two_factor_secret(self):
        self.two_factor_secret = base64.b32encode(os.urandom(10)).decode('utf-8')

    def get_otp_uri(self):
        return f"otpauth://totp/CryptoTFG:{self.Email}?secret={self.two_factor_secret}&issuer=CryptoTFG"

    def get_reset_token(self, expires_sec=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.UserID})

    @staticmethod
    def verify_reset_token(token, max_age=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
        except Exception:
            return None
        return User.query.get(data['user_id'])


class Asset(db.Model):
    __tablename__ = 'Assets'

    AssetID = db.Column(db.Integer, primary_key=True)
    AssetAddress = db.Column(db.String(200))
    Name = db.Column(db.String(255))
    Symbol = db.Column(db.String(40), unique=True, nullable=False)
    Decimals = db.Column(db.Integer)
    Source = db.Column(db.String(50))
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)
    id_coin = db.Column(db.String(100))
    LogoURL = db.Column(db.String(1000))

    prices = db.relationship(
        'AssetPrice',
        backref='asset',
        lazy=True,
        cascade="all, delete-orphan"
    )


class AssetPrice(db.Model):
    __tablename__ = 'AssetPrices'

    PriceID = db.Column(db.Integer, primary_key=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    RecordedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    PriceUSD = db.Column(db.Numeric(18, 8), nullable=False)
    MarketCap = db.Column(db.Numeric(38, 18))
    TotalVolume = db.Column(db.Numeric(38, 18))
    FullyDilutedValuation = db.Column(db.Numeric(38, 4))
    CirculatingSupply = db.Column(db.Numeric(38, 4))
    TotalSupply = db.Column(db.Numeric(38, 4))
    MaxSupply = db.Column(db.Numeric(38, 4))
    ATH = db.Column(db.Numeric(38, 8))
    ATHDate = db.Column(db.DateTime)
    ATL = db.Column(db.Numeric(38, 8))
    ATLDate = db.Column(db.DateTime)
    PriceChange24hPct = db.Column(db.Numeric(18, 8))
    PriceChange7dPct = db.Column(db.Numeric(18, 8))
    PriceChange30dPct = db.Column(db.Numeric(18, 8))


class Transaction(db.Model):
    __tablename__ = 'Transactions'

    TransactionID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    TxHash = db.Column(db.String(100), nullable=False, unique=True)
    FromAddress = db.Column(db.String(120), nullable=False)
    ToAddress = db.Column(db.String(120), nullable=False)
    Amount = db.Column(db.Numeric(38, 18), nullable=False)
    AmountUSD = db.Column(db.Numeric(38, 18), nullable=True)
    Timestamp = db.Column(db.DateTime, nullable=False)

    asset = db.relationship('Asset', backref='transactions')


class NoticiaCripto(db.Model):
    __tablename__ = 'NoticiasCripto'

    NoticiaID = db.Column(db.Integer, primary_key=True)
    Activo = db.Column(db.String(10), nullable=False)
    FechaPublicacion = db.Column(db.DateTime, nullable=False)
    URL = db.Column(db.Text, nullable=False)
    Imagen = db.Column(db.Text)
    Titulo = db.Column(db.Text)


class PortfolioAsset(db.Model):
    __tablename__ = 'PortfolioAssets'

    PortfolioAssetID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    Quantity = db.Column(db.Numeric(38, 18), nullable=False)
    PurchaseValueUSD = db.Column(db.Numeric(38, 18), nullable=False)
    CurrentValueUSD = db.Column(db.Numeric(38, 18), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='portfolio_assets')
    asset = db.relationship('Asset', backref=db.backref('portfolio_entries', cascade="all, delete-orphan"))


class HolderCategory(db.Model):
    __tablename__ = 'HolderCategories'

    CategoryID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    MinBalance = db.Column(db.Numeric(38, 18), nullable=False)
    MaxBalance = db.Column(db.Numeric(38, 18), nullable=True)
    Icon = db.Column(db.String(255), nullable=True)

    holders = db.relationship('Holder', backref='category', lazy=True)


class Holder(db.Model):
    __tablename__ = 'Holders'

    HolderID = db.Column(db.Integer, primary_key=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    Address = db.Column(db.String(150), nullable=False)  # o incluso 200 si quieres cubrirte más
    Balance = db.Column(db.Numeric(38, 18), nullable=False)

    CategoryID = db.Column(db.Integer, db.ForeignKey('HolderCategories.CategoryID'), nullable=True)
    asset = db.relationship('Asset', backref='holders', lazy=True)


class WalletAddress(db.Model):
    __tablename__ = 'WalletAddresses'

    WalletID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=True)
    Address = db.Column(db.String(120), nullable=False)
    Symbol = db.Column(db.String(10), nullable=False)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=True)
    Source = db.Column(db.String(50), nullable=True)  # <- NUEVA COLUMNA para red: bsc, ethereum, polygon...
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='wallet_addresses')
    asset = db.relationship('Asset', backref='wallet_addresses')

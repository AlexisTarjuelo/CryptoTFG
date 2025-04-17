# app/models.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  # ❗ Importa la instancia compartida desde __init__.py

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
    Avatar = db.Column(db.String(200), nullable=False, default='default_dino.png')
    BiometricCredentialID = db.Column(db.String(500), nullable=True)
    BiometricPublicKey = db.Column(db.String(2000), nullable=True)
    SignCount = db.Column(db.Integer, default=0)

    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)

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

    prices = db.relationship('AssetPrice', backref='asset', lazy=True)

class AssetPrice(db.Model):
    __tablename__ = 'AssetPrices'

    PriceID = db.Column(db.Integer, primary_key=True)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID'), nullable=False)
    RecordedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    PriceUSD = db.Column(db.Numeric(18, 8), nullable=False)
    MarketCap = db.Column(db.Numeric(38, 18))
    TotalVolume = db.Column(db.Numeric(38, 18))
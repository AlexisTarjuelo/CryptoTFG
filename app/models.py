import os
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from . import db


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

    # Relaciones
    portfolio_assets = db.relationship('PortfolioAsset', backref='user', cascade='all, delete-orphan', lazy=True)
    wallet_addresses = db.relationship('WalletAddress', backref='user', cascade='all, delete-orphan', lazy=True)

    # ---------- Métodos ----------
    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)

    def generate_two_factor_secret(self):
        self.two_factor_secret = base64.b32encode(os.urandom(10)).decode('utf-8')

    def get_otp_uri(self):
        return f"otpauth://totp/CryptoTFG:{self.Email}?secret={self.two_factor_secret}&issuer=CryptoTFG"

    def enable_2fa(self):
        self.two_factor_enabled = True
        db.session.commit()

    def disable_2fa(self):
        self.two_factor_enabled = False
        self.two_factor_secret = None
        db.session.commit()

    def register_biometric(self, credential_id, public_key, sign_count):
        self.BiometricCredentialID = credential_id
        self.BiometricPublicKey = public_key
        self.SignCount = sign_count

    def update_profile(self, first_name=None, last_name=None, email=None, phone=None, avatar=None):
        if first_name: self.FirstName = first_name
        if last_name: self.LastName = last_name
        if email: self.Email = email
        if phone: self.Phone = phone
        if avatar: self.Avatar = avatar
        db.session.commit()

    def change_password(self, new_password):
        self.set_password(new_password)
        db.session.commit()

    def reset_security(self):
        self.disable_2fa()
        self.BiometricCredentialID = None
        self.BiometricPublicKey = None
        self.SignCount = 0
        db.session.commit()

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

    prices = db.relationship('AssetPrice', backref='asset', lazy=True, cascade="all, delete-orphan")
    portfolio_entries = db.relationship('PortfolioAsset', backref='asset', lazy=True, cascade="all, delete-orphan")
    wallet_addresses = db.relationship('WalletAddress', backref='asset', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='asset', lazy=True, cascade="all, delete-orphan")
    holders = db.relationship('Holder', backref='asset', lazy=True, cascade="all, delete-orphan")

    def update_fields(self, data: dict):
        self.Name = data.get('name', self.Name)
        self.Symbol = data.get('symbol', self.Symbol)
        self.AssetAddress = data.get('address', self.AssetAddress)
        self.Decimals = data.get('decimals', self.Decimals)
        self.Source = data.get('source', self.Source)
        db.session.commit()


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

class CryptoNews(db.Model):
    __tablename__ = 'CryptoNews'

    NewsID = db.Column(db.Integer, primary_key=True)
    Asset = db.Column(db.String(10), nullable=False)
    PublicationDate = db.Column(db.DateTime, nullable=False)
    URL = db.Column(db.Text, nullable=False)
    Image = db.Column(db.Text)
    Title = db.Column(db.Text)



class PortfolioAsset(db.Model):
    __tablename__ = 'PortfolioAssets'

    PortfolioAssetID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID', ondelete="CASCADE"), nullable=False)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID', ondelete="CASCADE"), nullable=False)
    Quantity = db.Column(db.Numeric(38, 18), nullable=False)
    PurchaseValueUSD = db.Column(db.Numeric(38, 18), nullable=False)
    CurrentValueUSD = db.Column(db.Numeric(38, 18), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

    def update_current_value(self, current_price):
        self.CurrentValueUSD = float(self.Quantity) * float(current_price)

    @staticmethod
    def add_or_update(user_id, asset, quantity, purchase_value_usd, current_price):
        existing = PortfolioAsset.query.filter_by(UserID=user_id, AssetID=asset.AssetID).first()
        if existing:
            existing.Quantity += quantity
            existing.PurchaseValueUSD += purchase_value_usd
            existing.update_current_value(current_price)
        else:
            new_entry = PortfolioAsset(
                UserID=user_id,
                AssetID=asset.AssetID,
                Quantity=quantity,
                PurchaseValueUSD=purchase_value_usd,
                CurrentValueUSD=current_price * quantity
            )
            db.session.add(new_entry)
        db.session.commit()


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
    Address = db.Column(db.String(150), nullable=False)
    Balance = db.Column(db.Numeric(38, 18), nullable=False)
    CategoryID = db.Column(db.Integer, db.ForeignKey('HolderCategories.CategoryID'), nullable=True)


class WalletAddress(db.Model):
    __tablename__ = 'WalletAddresses'

    WalletID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID', ondelete="CASCADE"), nullable=True)
    Address = db.Column(db.String(120), nullable=False)
    Symbol = db.Column(db.String(10), nullable=False)
    AssetID = db.Column(db.Integer, db.ForeignKey('Assets.AssetID', ondelete="CASCADE"), nullable=True)
    Source = db.Column(db.String(50), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)












    

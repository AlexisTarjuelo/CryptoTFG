import os

class Config:
    # Seguridad
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-super-segura'

    # Base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API externa
    BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', 'clave_api_bscscan_temporal')

    # 💌 Flask-Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.zoho.eu')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'CryptoTFG <noreply@cryptotfg.com>')

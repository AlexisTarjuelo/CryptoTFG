import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-super-segura'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', 'clave_api_bscscan_temporal')

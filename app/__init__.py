# app/__init__.py

from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

load_dotenv()

db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()  # 💌 nuevo

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.debug = True

    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)  # 💌 inicialización

    from .routes import auth_bp
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_year():
        return {
            "year": datetime.now().year,
            "start_year": 2025
        }

    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        if user_id:
            from app.models import User
            g.user = User.query.get(user_id)
        else:
            g.user = None

    return app

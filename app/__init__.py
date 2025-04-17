# app/__init__.py
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

load_dotenv()
db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.debug = True

    db.init_app(app)
    csrf.init_app(app)

    # ✅ Aquí registras el blueprint
    from .routes import auth_bp
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    # ✅ Context processor global para el footer dinámico
    @app.context_processor
    def inject_year():
        return {
            "year": datetime.now().year,
            "start_year": 2025  # año en que empezó tu proyecto
        }

    # ✅ Cargar usuario logueado para acceder como g.user
    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        if user_id:
            from app.models import User
            g.user = User.query.get(user_id)
        else:
            g.user = None

    return app
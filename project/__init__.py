from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
from .models import db
from .auth import login_manager

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # Load config
    app.config.from_object('config.Config')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from . import main, auth, models
        
        # Register Blueprints
        app.register_blueprint(auth.auth_bp)
        app.register_blueprint(main.main_bp)

        # Create database tables if they don't exist
        db.create_all()

    return app

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

from app.models.db_config import get_sqlalchemy_config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config=None):
    app = Flask(__name__)
    
    # Load database configuration
    app.config.update(get_sqlalchemy_config())
    
    # Additional configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    
    # Override with passed config if any
    if config:
        app.config.update(config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main.bp)
    
    return app

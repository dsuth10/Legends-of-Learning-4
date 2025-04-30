from flask import Flask
from app.models import db  # Use the single db instance from app.models
from flask_login import LoginManager
from flask_migrate import Migrate
import os

from app.models.db_config import get_sqlalchemy_config
from app.models.db_maintenance import check_db_version, start_weekly_integrity_check

# Initialize extensions
login_manager = LoginManager()
migrate = Migrate()

def create_app(config=None):
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
    
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
    
    # Flask-Login user loader
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes import init_app
    init_app(app)

    # --- DB maintenance: version check and weekly integrity check ---
    check_db_version(app)
    start_weekly_integrity_check(app)
    # --------------------------------------------------------------

    return app

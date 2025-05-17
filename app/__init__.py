from flask import Flask
from app.models import db  # Use the single db instance from app.models
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from flask_jwt_extended import JWTManager

from app.models.db_config import get_sqlalchemy_config
from app.models.db_maintenance import check_db_version, start_weekly_integrity_check

# Initialize extensions
login_manager = LoginManager()
migrate = Migrate()

def create_app(config=None):
    app = Flask(__name__, template_folder="templates", static_folder="../static")
    
    # Load database configuration
    app.config.update(get_sqlalchemy_config())
    
    # Additional configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    app.config['TEACHER_ACCESS_CODE'] = os.environ.get('TEACHER_ACCESS_CODE', 'default-secure-code-for-dev')
    
    # Session and cookie security settings
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour in seconds
    app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookies over HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JS access to cookies
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Mitigate CSRF
    # For production, ensure HTTPS is enforced (see Flask-Talisman or reverse proxy setup)
    
    # Override with passed config if any
    if config:
        app.config.update(config)

    # Remove pool options for in-memory SQLite
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:///:memory:'):
        engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        for k in ['pool_size', 'max_overflow', 'pool_timeout']:
            engine_options.pop(k, None)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    jwt = JWTManager(app)
    
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

from flask import Flask
from app.models import db, init_db  # Use the single db instance from app.models
from flask_login import LoginManager
from flask_migrate import Migrate
import os
import logging
from logging.handlers import RotatingFileHandler
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
    # Only use secure cookies in production (HTTPS required)
    # In development, set to False to allow HTTP
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JS access to cookies
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Mitigate CSRF
    # For production, ensure HTTPS is enforced (see Flask-Talisman or reverse proxy setup)
    
    # Override with passed config if any
    if config:
        app.config.update(config)

    # Remove pool options for in-memory SQLite
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite://'):
        engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        engine_options['connect_args'] = {'check_same_thread': False}
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    if uri.startswith('sqlite:///:memory:'):
        engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        for k in ['pool_size', 'max_overflow', 'pool_timeout']:
            engine_options.pop(k, None)
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    
    # Initialize extensions
    # Initialize extensions
    # db.init_app(app) # Moved to init_db
    init_db(app) # Register models and init db
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
    
    # Register user lookup loader for JWT
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(identity)
    
    # Register blueprints
    from app.routes import init_app
    init_app(app)

    # --- DB maintenance: version check and weekly integrity check ---
    # check_db_version(app)
    # start_weekly_integrity_check(app)
    # --------------------------------------------------------------

    # Configure logging
    if not app.debug:
        # Production logging: log to file
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/legends_of_learning.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Legends of Learning startup')
    else:
        # Development logging: log to console with more detail
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
    
    # Set logging level for SQLAlchemy to reduce noise
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    # Register CLI commands
    from app.commands import seed_db_command
    app.cli.add_command(seed_db_command)

    # --- Populate Equipment Table from Hardcoded Data (if empty) ---
    from app.models.equipment_data import EQUIPMENT_DATA
    from app.models.equipment import Equipment
    from sqlalchemy import inspect
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table(Equipment.__tablename__):
            if Equipment.query.count() == 0:
                for item in EQUIPMENT_DATA:
                    type_value = item['type'].value if hasattr(item['type'], 'value') else item['type']
                    slot_value = item['slot'].value if hasattr(item['slot'], 'value') else item['slot']
                    eq = Equipment(
                        name=item['name'],
                        description=item['description'],
                        type=type_value,
                        slot=slot_value,
                        cost=item['cost'],
                        level_requirement=item['level_requirement'],
                        health_bonus=item['health_bonus'],
                        power_bonus=item['power_bonus'],
                        defense_bonus=item['defense_bonus'],
                        rarity=item['rarity'],
                        image_url=item['image_url'],
                        class_restriction=item.get('class_restriction'),
                    )
                    db.session.add(eq)
                db.session.commit()
    # --------------------------------------------------------------

    return app

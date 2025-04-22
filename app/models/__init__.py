from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    
    # Import models here to ensure they are registered with SQLAlchemy
    from app.models.character import Character
    from app.models.ability import Ability, CharacterAbility
    
    # Create tables
    with app.app_context():
        db.create_all()


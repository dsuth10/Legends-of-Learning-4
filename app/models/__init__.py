from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    db.init_app(app)
    
    # Import models here to ensure they are registered with SQLAlchemy
    from app.models.base import Base
    from app.models.user import User, UserRole
    from app.models.classroom import Classroom, class_students
    from app.models.character import Character
    from app.models.clan import Clan
    from app.models.equipment import Equipment, EquipmentType, EquipmentSlot, Inventory
    from app.models.ability import Ability, AbilityType, CharacterAbility
    
    # Create tables
    with app.app_context():
        db.create_all()


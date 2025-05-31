from flask_sqlalchemy import SQLAlchemy

from app.models.base import Base  # <-- Re-export Base
from .db_config import db
from app.models.achievement_badge import AchievementBadge
from app.models.item import Item

__all__ = [
    'db',
    'Base',
]

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
    from app.models.student import Student
    from app.models.assist_log import AssistLog
    from app.models.clan_progress import ClanProgressHistory
    
    # Create tables
    # with app.app_context():
    #     db.create_all()


from datetime import datetime
from app.models.base import Base
from app.models import db
from sqlalchemy import JSON
from enum import Enum

class BattleStatus(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    FLED = "fled"

class Monster(Base):
    """Enemy definitions for battles."""
    __tablename__ = 'monsters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    image_url = db.Column(db.String(256), nullable=True)
    level = db.Column(db.Integer, default=1)
    
    # Stats
    health = db.Column(db.Integer, default=100)
    attack = db.Column(db.Integer, default=10)
    defense = db.Column(db.Integer, default=5)
    
    # Rewards
    xp_reward = db.Column(db.Integer, default=50)
    gold_reward = db.Column(db.Integer, default=10)

    def __repr__(self):
        return f'<Monster {self.name} Lv.{self.level}>'

class Battle(Base):
    """Active battle session between a student and a monster."""
    __tablename__ = 'battles'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    monster_id = db.Column(db.Integer, db.ForeignKey('monsters.id', ondelete='CASCADE'), nullable=False)
    question_set_id = db.Column(db.Integer, db.ForeignKey('question_sets.id', ondelete='SET NULL'), nullable=True)
    
    # Current State
    player_health = db.Column(db.Integer, nullable=False)
    player_max_health = db.Column(db.Integer, nullable=False)
    monster_health = db.Column(db.Integer, nullable=False)
    monster_max_health = db.Column(db.Integer, nullable=False)
    
    status = db.Column(db.Enum(BattleStatus), default=BattleStatus.ACTIVE)
    
    # Log of turns: [{turn: 1, action: "attack", damage: 10, question_id: 5, correct: true}, ...]
    turn_log = db.Column(JSON, default=list)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    student = db.relationship('Student', backref='battles')
    monster = db.relationship('Monster')
    question_set = db.relationship('QuestionSet')

    def __repr__(self):
        return f'<Battle {self.id} - {self.status.value}>'

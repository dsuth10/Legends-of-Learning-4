from datetime import datetime
from enum import Enum
from typing import List, Optional
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, Field

from app.models import db
from app.models.base import Base
from app.models.equipment import Equipment
from app.models.ability import Ability

class QuestStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class QuestType(str, Enum):
    STORY = "story"
    DAILY = "daily"
    WEEKLY = "weekly"
    ACHIEVEMENT = "achievement"
    EVENT = "event"

class RewardType(str, Enum):
    EXPERIENCE = "experience"
    GOLD = "gold"
    EQUIPMENT = "equipment"
    ABILITY = "ability"
    CLAN_EXPERIENCE = "clan_experience"
    SPECIAL_CURRENCY = "special_currency"

class Quest(Base):
    """Quest model representing available quests in the game."""
    
    __tablename__ = 'quests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(QuestType), nullable=False)
    level_requirement = db.Column(db.Integer, default=1, nullable=False)
    
    # Quest requirements and completion criteria stored as JSON
    requirements = db.Column(JSON, nullable=False, default=dict)
    completion_criteria = db.Column(JSON, nullable=False, default=dict)
    
    # Time constraints (optional)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    time_limit_hours = db.Column(db.Integer, nullable=True)  # Time limit once started
    
    # Quest chain/prerequisites
    parent_quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    rewards = db.relationship('Reward', backref='quest', lazy='dynamic', cascade='all, delete-orphan')
    consequences = db.relationship('Consequence', backref='quest', lazy='dynamic', cascade='all, delete-orphan')
    quest_logs = db.relationship('QuestLog', backref='quest', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_quest_type', 'type'),  # For filtering quests by type
        db.Index('idx_quest_level', 'level_requirement'),  # For level-appropriate quests
        db.Index('idx_quest_dates', 'start_date', 'end_date'),  # For active quests
    )
    
    def __init__(self, title, description, type, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.type = type
    
    def is_available(self, character):
        """Check if quest is available for a character."""
        if self.level_requirement > character.level:
            return False
        
        if self.start_date and datetime.utcnow() < self.start_date:
            return False
        
        if self.end_date and datetime.utcnow() > self.end_date:
            return False
        
        # Check if prerequisite quest is completed
        if self.parent_quest_id:
            parent_log = QuestLog.query.filter_by(
                quest_id=self.parent_quest_id,
                character_id=character.id,
                status=QuestStatus.COMPLETED
            ).first()
            if not parent_log:
                return False
        
        return True
    
    def __repr__(self):
        return f'<Quest {self.title} ({self.type.value})>'

class QuestLog(Base):
    """Model for tracking character progress on quests."""
    
    __tablename__ = 'quest_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum(QuestStatus), default=QuestStatus.NOT_STARTED, nullable=False)
    
    # Progress tracking
    progress_data = db.Column(JSON, nullable=False, default=dict)  # Store progress details
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    character = db.relationship('Character', backref=db.backref('quest_logs', lazy='dynamic'))
    
    __table_args__ = (
        db.Index('idx_questlog_character', 'character_id'),  # For character's quests
        db.Index('idx_questlog_status', 'character_id', 'status'),  # For filtering by status
        db.UniqueConstraint('character_id', 'quest_id', name='uq_character_quest'),  # One log per quest
    )
    
    def start_quest(self):
        """Start the quest."""
        if self.status != QuestStatus.NOT_STARTED:
            raise ValueError("Quest has already been started")
        
        self.status = QuestStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.save()
    
    def update_progress(self, progress_data):
        """Update quest progress."""
        self.progress_data.update(progress_data)
        self.save()
    
    def complete_quest(self):
        """Mark quest as completed and distribute rewards."""
        if self.status != QuestStatus.IN_PROGRESS:
            raise ValueError("Quest must be in progress to complete")
        
        self.status = QuestStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        
        # Distribute rewards
        for reward in self.quest.rewards:
            reward.distribute(self.character)
        
        self.save()
    
    def fail_quest(self):
        """Mark quest as failed and apply consequences."""
        self.status = QuestStatus.FAILED
        self.completed_at = datetime.utcnow()
        
        # Apply consequences
        for consequence in self.quest.consequences:
            consequence.apply(self.character)
        
        self.save()
    
    def __repr__(self):
        return f'<QuestLog {self.quest.title} - {self.status.value}>'

class Reward(Base):
    """Model for quest rewards."""
    
    __tablename__ = 'rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.Enum(RewardType), nullable=False)
    amount = db.Column(db.Integer, nullable=False, default=0)  # For XP, gold, etc.
    
    # Optional foreign keys for specific rewards
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id', ondelete='SET NULL'), nullable=True)
    ability_id = db.Column(db.Integer, db.ForeignKey('abilities.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships for specific rewards
    equipment = db.relationship('Equipment')
    ability = db.relationship('Ability')
    
    def distribute(self, character):
        """Distribute the reward to a character."""
        if self.type == RewardType.EXPERIENCE:
            character.gain_experience(self.amount)
        
        elif self.type == RewardType.GOLD:
            # Assuming character has a gold attribute
            character.gold += self.amount
            character.save()
        
        elif self.type == RewardType.EQUIPMENT and self.equipment:
            inventory = Inventory(
                character_id=character.id,
                equipment_id=self.equipment_id
            )
            inventory.save()
        
        elif self.type == RewardType.ABILITY and self.ability:
            char_ability = CharacterAbility(
                character_id=character.id,
                ability_id=self.ability_id
            )
            char_ability.save()
        
        elif self.type == RewardType.CLAN_EXPERIENCE and character.clan:
            character.clan.gain_experience(self.amount)
    
    def __repr__(self):
        return f'<Reward {self.type.value} ({self.amount})>'

class Consequence(Base):
    """Model for quest failure consequences."""
    
    __tablename__ = 'consequences'
    
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Penalty values
    experience_penalty = db.Column(db.Integer, default=0)
    gold_penalty = db.Column(db.Integer, default=0)
    health_penalty = db.Column(db.Integer, default=0)
    
    def apply(self, character):
        """Apply the consequence to a character."""
        if self.experience_penalty > 0:
            character.experience = max(0, character.experience - self.experience_penalty)
        
        if self.gold_penalty > 0:
            character.gold = max(0, character.gold - self.gold_penalty)
        
        if self.health_penalty > 0:
            character.take_damage(self.health_penalty)
        
        character.save()
    
    def __repr__(self):
        return f'<Consequence for {self.quest.title}>'

# Pydantic models for validation
class QuestBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1)
    type: QuestType
    level_requirement: int = Field(default=1, ge=1)
    requirements: dict = Field(default_factory=dict)
    completion_criteria: dict = Field(default_factory=dict)
    time_limit_hours: Optional[int] = Field(None, ge=0)

class QuestCreate(QuestBase):
    pass

class QuestUpdate(QuestBase):
    pass

class QuestRead(QuestBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 